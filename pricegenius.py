import os
import requests
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# API Keys
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# --- Streamlit Page Setup ---
st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")

st.markdown("""
    <h1 style='text-align:center; font-size:42px;'>🛫 PricePilot</h1>
    <p style='text-align:center; color:gray;'>
        Compare live prices across BestBuy, Walmart, and Google Shopping — powered by AI.
    </p>
""", unsafe_allow_html=True)

# --- Fetch Prices Function ---
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
            title = r.get("title", "Unknown Product")
            store = r.get("source", None)
            link = r.get("link", "")
            price = r.get("extracted_price", None) or r.get("price", None)

            # Extract a readable store name from link if missing
            if not store and link:
                try:
                    store = link.split("/")[2].replace("www.", "")
                except Exception:
                    store = "Unknown Store"

            # Extract display domain for link
            if link and link.startswith("http"):
                display_link = link.split("/")[2].replace("www.", "")
            else:
                display_link = "N/A"

            results.append({
                "store": store or "Unknown Store",
                "price": price,
                "link": link if link.startswith("http") else "",
                "display_link": display_link
            })
    return results

# --- Analyze Prices Function ---
def analyze_prices(prices):
    if not prices:
        return "No price data available."

    table = "\n".join([f"{p['store']}: ${p['price']}" for p in prices])
    prompt = (
        f"Here are product prices:\n{table}\n\n"
        "Which store offers the best deal and why? Keep it under 3 sentences, friendly tone, end with an emoji."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
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
        # --- Price Results ---
        st.markdown(
            "<h3 style='color:#f5b400; font-weight:800;'>💰 Price Results</h3>",
            unsafe_allow_html=True,
        )

        for item in prices:
            store = item.get("store", "Unknown Store")
            price = item.get("price", "N/A")
            link = item.get("link", "")
            display_link = item.get("display_link", "N/A")

            st.markdown(
                f"""
                <div style='background-color:#f9f9f9; border-radius:10px; padding:10px; margin:6px 0;'>
                    <b style='font-size:18px;'>{store}</b> —
                    <span style='color:#16a34a; font-weight:bold;'>${price}</span>
                    {"<a href='" + link + "' target='_blank' style='text-decoration:none; color:#2563eb;'>🌐 " + display_link + "</a>" if link else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # --- AI Recommendation ---
        analysis = analyze_prices(prices)
        st.markdown("""
            <div style='margin-top:25px; background-color:#f0fdf4; border-left:5px solid #22c55e;
                        padding:15px; border-radius:10px;'>
                <h4 style='color:#047857; margin-bottom:10px;'>🧠 AI Recommendation</h4>
            """, unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:16px;'>{analysis}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning("No prices found. Try another product name!")

# --- Footer ---
st.markdown("""
    <hr>
    <center>
        <p style='color:gray; font-size:13px;'>
            Built with ❤️ by Team PricePilot — powered by Streamlit, SerpAPI, and OpenAI
        </p>
    </center>
""", unsafe_allow_html=True)
