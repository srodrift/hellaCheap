import os
import requests
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# Streamlit Setup
st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")

st.markdown("""
    <h1 style='text-align:center; font-size:42px;'>🛫 PricePilot</h1>
    <p style='text-align:center; color:gray;'>
        Compare live prices across BestBuy, Walmart, and Google Shopping — powered by AI.
    </p>
""", unsafe_allow_html=True)


# --- Fetch Prices ---
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
            store = r.get("source", "Unknown Store")
            link = r.get("link", "")
            price = r.get("extracted_price") or r.get("price", None)

            # Extract domain name if available
            if link and link.startswith("http"):
                domain = link.split("/")[2].replace("www.", "")
            else:
                domain = "N/A"

            results.append({
                "title": title,
                "store": store,
                "price": price,
                "link": link,
                "domain": domain
            })
    return results


# --- Analyze Prices ---
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
        st.subheader("💰 Price Results")

        for p in prices:
            store = p.get("store", "Unknown Store")
            price = p.get("price", "N/A")
            link = p.get("link", "")
            domain = p.get("domain", "N/A")
            title = p.get("title", "")

            # Use Streamlit markdown links — fully compatible
            if link:
                st.markdown(f"**{store}** — ${price}  \n[{domain}]({link})", unsafe_allow_html=False)
            else:
                st.markdown(f"**{store}** — ${price}  \n_No link available_")

        st.markdown("---")

        # --- AI Recommendation ---
        analysis = analyze_prices(prices)
        st.markdown("### 🧠 AI Recommendation")
        st.write(analysis)

    else:
        st.warning("No prices found. Try another product name!")


# --- Footer ---
st.markdown("""
---
<center>
<p style='color:gray; font-size:13px;'>
Built with ❤️ by Team PricePilot — powered by Streamlit, SerpAPI, and OpenAI
</p>
</center>
""", unsafe_allow_html=True)
