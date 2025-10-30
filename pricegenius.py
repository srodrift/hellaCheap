import os
import requests
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Keys
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# Page setup
st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")

st.markdown(
    """
    <h1 style='text-align:center; font-size:42px;'>🛫 PricePilot</h1>
    <p style='text-align:center; color:gray;'>
        Compare live prices across BestBuy, Walmart, and Google Shopping — powered by AI.
    </p>
    """,
    unsafe_allow_html=True
)

# --- Function: Fetch prices ---
def fetch_prices(product):
    if not SERPAPI_KEY:
        st.error("❌ Missing SERPAPI_KEY. Please set it in Streamlit Secrets.")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": product,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "gl": "us",
        "num": 10,
    }

    response = requests.get(url, params=params)
    data = response.json()
    results = []

    if "shopping_results" in data:
        for r in data["shopping_results"][:5]:
            link = r.get("link", "")
            domain = link.split("/")[2].replace("www.", "") if link else "unknown"
            results.append({
                "store": r.get("source", domain),
                "price": r.get("price"),
                "link": f"https://{domain}" if domain else "N/A"
            })
    return results

# --- Function: Analyze prices with OpenAI ---
def analyze_prices(prices):
    if not prices:
        return "No price data available."

    table = "\n".join([f"{p['store']}: ${p['price']}" for p in prices])
    summary_prompt = (
        f"Here are product prices:\n{table}\n\n"
        "Which store offers the best deal, and why? Write the answer in 2 sentences, "
        "friendly and clear, ending with an emoji."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({str(e)})"

# --- UI Input ---
product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

if product:
    with st.spinner("🔍 Searching the web for the best deals..."):
        prices = fetch_prices(product)

    if prices:
        # --- Display Prices ---
        st.markdown(
            "<h3 style='color:#f5b400; font-weight:800;'>💰 Price Results</h3>",
            unsafe_allow_html=True,
        )

        for item in prices:
            st.markdown(
                f"""
                <div style='background-color:#f9f9f9; border-radius:10px; padding:10px; margin:6px 0;'>
                    <b style='font-size:18px;'>{item['store']}</b> —
                    <span style='color:#16a34a; font-weight:bold;'>${item['price']}</span>
                    <a href='{item['link']}' target='_blank' style='text-decoration:none; color:#2563eb;'>🌐 {item['link'].split('//')[1]}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # --- AI Recommendation ---
        analysis = analyze_prices(prices)
        st.markdown(
            """
            <div style='margin-top:25px; background-color:#f0fdf4; border-left:5px solid #22c55e;
                        padding:15px; border-radius:10px;'>
                <h4 style='color:#047857; margin-bottom:10px;'>🧠 AI Recommendation</h4>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"<p style='font-size:16px;'>{analysis}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning("No prices found. Try another product name!")

# --- Footer ---
st.markdown(
    """
    <hr>
    <center>
        <p style='color:gray; font-size:13px;'>
            Built with ❤️ by Team PricePilot — powered by Streamlit, SerpAPI, and OpenAI
        </p>
    </center>
    """,
    unsafe_allow_html=True,
)
