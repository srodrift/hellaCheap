import os
import json
import requests
import streamlit as st
import pandas as pd
from openai import OpenAI

# --- API Keys ---
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Initialize OpenAI client ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Streamlit app setup ---
st.set_page_config(page_title="PricePilot", page_icon="🛫")
st.title("🛫 PricePilot")
st.write("Compare live prices across BestBuy, Walmart, and Google Shopping.")

# --- Function to fetch prices from SerpAPI ---
def fetch_prices(product):
    if not SERPAPI_KEY:
        st.error("❌ Missing SERPAPI_KEY. Please add it in Streamlit secrets.")
        return []
    url = f"https://serpapi.com/search.json?q={product}&engine=google_shopping&api_key={SERPAPI_KEY}"
    r = requests.get(url)
    data = r.json()
    results = []
    for item in data.get("shopping_results", [])[:5]:
        results.append({
            "Store": item.get("source"),
            "Price ($)": item.get("extracted_price"),
            "Link": item.get("link")
        })
    return results

# --- Function to analyze prices using OpenAI ---
def analyze_prices(prices):
    if not OPENAI_API_KEY:
        return "❌ Missing OPENAI_API_KEY. Please add it in Streamlit secrets."

    summary_prompt = f"""
    You are a shopping analyst. Given this list of store prices, find the cheapest option and
    explain in plain English which store provides the best value and why.
    {json.dumps(prices, indent=2)}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({str(e)[:100]}...)"

# --- UI Input ---
product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

if st.button("🔍 Search"):
    if not product:
        st.warning("Please enter a product name.")
    else:
        with st.spinner("Fetching live prices..."):
            prices = fetch_prices(product)

        if prices:
            df = pd.DataFrame(prices)
            st.subheader("💰 Price Results")
            st.dataframe(df, use_container_width=True)

            with st.spinner("Analyzing best deal with AI..."):
                analysis = analyze_prices(prices)

            st.subheader("🧠 AI Recommendation")
            st.markdown(f"✅ **{analysis}**")
        else:
            st.error("No results found. Try another product name.")

# --- Footer ---
st.markdown("---")
st.caption("Built with ❤️ using SerpAPI + OpenAI + Streamlit by @srodrift")
