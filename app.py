import streamlit as st
import yfinance as yf
import requests
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from streamlit_searchbox import st_searchbox

FINNHUB_API_KEY = "d6org59r01qmqugc3g60d6org59r01qmqugc3g6g"

QUICK_PICKS = [
    {"name": "Apple",    "ticker": "AAPL",  "domain": "apple.com"},
    {"name": "Tesla",    "ticker": "TSLA",  "domain": "tesla.com"},
    {"name": "NVIDIA",   "ticker": "NVDA",  "domain": "nvidia.com"},
    {"name": "Amazon",   "ticker": "AMZN",  "domain": "amazon.com"},
    {"name": "Meta",     "ticker": "META",  "domain": "meta.com"},
    {"name": "Google",   "ticker": "GOOGL", "domain": "google.com"},
]

NON_US_SUFFIXES = [".NS", ".BO", ".L", ".HK", ".AX", ".TO", ".DE", ".PA"]

def logo_url(domain):
    return f"https://cdn.brandfetch.io/{domain}/w/400/h/400"

def search_stocks(query):
    if not query or len(query) < 1:
        return []
    url = f"https://finnhub.io/api/v1/search?q={query}&token={FINNHUB_API_KEY}"
    res = requests.get(url).json()
    results = res.get("result", [])
    results = [r for r in results if r.get("type") == "Common Stock"][:10]
    return [f"{r['description']} ({r['displaySymbol']})" for r in results]

st.set_page_config(page_title="Market Mind", layout="wide")

# ── LANDING HEADER ──
st.title("🧠 Market Mind — AI Financial Terminal")
st.markdown("_Real-time stock data, live news, and AI-powered sentiment analysis — all in one place._")
st.divider()

# ── QUICK PICKS ──
st.markdown("**⚡ Quick Pick**")
cols = st.columns(6)
quick_pick = None

for i, stock in enumerate(QUICK_PICKS):
    with cols[i]:
        st.image(logo_url(stock["domain"]), width=48)
        if st.button(stock["name"], key=stock["ticker"]):
            quick_pick = stock["ticker"]

st.divider()

# ── SEARCHBOX ──
st.subheader("🔍 Or Search for Any Stock")
selection = st_searchbox(
    search_stocks,
    placeholder="Start typing a company name or ticker...",
    key="stock_search"
)

ticker = None

if quick_pick:
    ticker = quick_pick
    st.success(f"Selected: **{ticker}**")
elif selection:
    ticker = selection.split("(")[-1].replace(")", "").strip()

if ticker:
    st.divider()

    # ── NON-US WARNING ──
    if any(ticker.endswith(suffix) for suffix in NON_US_SUFFIXES):
        st.info("ℹ️ News and sentiment analysis is available for US-listed stocks only. Price data below is still accurate.")

    # ── STOCK DATA ──
    stock = yf.Ticker(ticker)
    info = stock.info

    website = info.get("website", "")
    if website:
        domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        col_logo, col_title = st.columns([1, 10])
        with col_logo:
            st.image(logo_url(domain), width=60)
        with col_title:
            st.subheader(f"{info.get('longName', ticker)} ({ticker})")
    else:
        st.subheader(f"📈 {ticker} — Live Market Data")

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
    if not any(ticker.endswith(suffix) for suffix in NON_US_SUFFIXES):
        st.subheader("📰 Latest News & Sentiment Analysis")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from=2025-01-01&to=2026-12-31&token={FINNHUB_API_KEY}"
        response = requests.get(url)
        news = response.json()

        analyzer = SentimentIntensityAnalyzer()
        weighted_scores = []
        total_weight = 0
        now = datetime.now().timestamp()

        if news and isinstance(news, list):
            news_sorted = sorted(news, key=lambda x: x.get("datetime", 0), reverse=True)[:50]

            for i, article in enumerate(news_sorted):
                headline = article.get("headline", "")
                pub_time = article.get("datetime", now)
                score = analyzer.polarity_scores(headline)["compound"]

                age_days = (now - pub_time) / 86400
                weight = 1 / (1 + age_days)
                weighted_scores.append(score * weight)
                total_weight += weight

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