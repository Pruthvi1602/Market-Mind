import streamlit as st
import yfinance as yf
import requests
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

FINNHUB_API_KEY = "d6org59r01qmqugc3g60d6org59r01qmqugc3g6g"

st.set_page_config(page_title="Market Mind", layout="wide")
st.title("🧠 Market Mind — AI Financial Terminal")

# ── SEARCH ──
st.subheader("🔍 Search for a Stock")
query = st.text_input("Type a company name or ticker (e.g. Apple, TSLA, Reliance)", value="")

ticker = None

if query:
    search_url = f"https://finnhub.io/api/v1/search?q={query}&token={FINNHUB_API_KEY}"
    res = requests.get(search_url).json()
    results = res.get("result", [])
    results = [r for r in results if r.get("type") == "Common Stock"][:10]

    if results:
        options = [f"{r['description']} ({r['displaySymbol']})" for r in results]
        selection = st.selectbox("Select the company you mean:", options)
        ticker = selection.split("(")[-1].replace(")", "").strip()
    else:
        st.warning("No results found. Try a different search term.")

if ticker:
    # ── STOCK DATA ──
    st.subheader(f"📈 {ticker} — Live Market Data")
    stock = yf.Ticker(ticker)
    info = stock.info

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${info.get('currentPrice', 'N/A')}")
    col2.metric("Market Cap", f"${info.get('marketCap', 0):,}")
    col3.metric("52W High", f"${info.get('fiftyTwoWeekHigh', 'N/A')}")
    col4.metric("52W Low", f"${info.get('fiftyTwoWeekLow', 'N/A')}")

    # ── PRICE CHART ──
    st.subheader("📊 Price History (6 Months)")
    hist = stock.history(period="6mo")
    if not hist.empty:
        st.line_chart(hist["Close"])
    else:
        st.warning("No historical data found.")

    # ── NEWS + SENTIMENT ──
    st.subheader("📰 Latest News & Sentiment Analysis")
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from=2025-01-01&to=2026-12-31&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    news = response.json()

    analyzer = SentimentIntensityAnalyzer()
    weighted_scores = []
    total_weight = 0
    now = datetime.now().timestamp()

    if news:
        # Sort by date, newest first
        news_sorted = sorted(news, key=lambda x: x.get("datetime", 0), reverse=True)[:50]

        for i, article in enumerate(news_sorted):
            headline = article.get("headline", "")
            pub_time = article.get("datetime", now)
            score = analyzer.polarity_scores(headline)["compound"]

            # Recency weight: newer articles get higher weight
            # Article age in days
            age_days = (now - pub_time) / 86400
            weight = 1 / (1 + age_days)

            weighted_scores.append(score * weight)
            total_weight += weight

            # Only display top 8 in UI
            if i < 8:
                if score >= 0.05:
                    sentiment = "🟢 Positive"
                elif score <= -0.05:
                    sentiment = "🔴 Negative"
                else:
                    sentiment = "🟡 Neutral"

                st.markdown(f"**{headline}**")
                st.caption(f"Sentiment: {sentiment} (score: {score:.2f}) | [Read more]({article.get('url', '#')})")
                st.divider()

        if len(news_sorted) > 8:
            st.caption(f"_Showing 8 of {len(news_sorted)} headlines analysed for the verdict._")
    else:
        st.info("No news articles found for this ticker.")

    # ── FINAL VERDICT ──
    st.subheader("🤖 AI Verdict")
    if weighted_scores and total_weight > 0:
        avg = sum(weighted_scores) / total_weight
        n = len(weighted_scores)

        if avg >= 0.05:
            verdict = "📈 BULLISH — Market sentiment is positive. Analysts may view this as a buying opportunity."
            color = "green"
        elif avg <= -0.05:
            verdict = "📉 BEARISH — Market sentiment is negative. Exercise caution."
            color = "red"
        else:
            verdict = "➡️ NEUTRAL — Sentiment is mixed. Monitor the stock closely."
            color = "orange"

        st.markdown(f"<h3 style='color:{color}'>{verdict}</h3>", unsafe_allow_html=True)
        st.caption(f"Based on recency-weighted average sentiment score of {avg:.3f} across {n} headlines. Recent news weighted higher.")
    else:
        st.info("Not enough data to generate a verdict.")