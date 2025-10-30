import os
import requests
import streamlit as st
from openai import OpenAI

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Initialize client
client = OpenAI(api_key=OPENAI_API_KEY)

# Streamlit UI
st.set_page_config(page_title="PricePilot", page_icon="🛫")
st.title("🛫 PricePilot")
st.write("Compare live prices across BestBuy, Walmart, and Google Shopping.")

# Product input
product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

def fetch_prices(product_name):
    if not SERPAPI_KEY:
        st.error("❌ Missing SERPAPI_KEY in Streamlit Secrets.")
        return []
    url = f"https://serpapi.com/search.json?q={product_name}&engine=google_shopping&api_key={SERPAPI_KEY}"
    r = requests.get(url)
    data = r.json()
    results = []
    for item in data.get("shopping_results", [])[:5]:
        results.append({
            "store": item.get("source"),
            "price": item.get("extracted_price"),
            "link": item.get("link"),
        })
    return results

def analyze_prices(prices):
    if not OPENAI_API_KEY:
        st.error("❌ Missing OPENAI_API_KEY in Streamlit Secrets.")
        return None

    summary_prompt = f"Here are product prices: {prices}. Which store offers the best deal and why?"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": summary_prompt}]
    )
    return response.choices[0].message.content.strip()

if product:
    with st.spinner("Fetching prices..."):
        prices = fetch_prices(product)
    if prices:
        st.subheader("💰 Price Results:")
        st.json(prices)
        with st.spinner("Analyzing best option..."):
            analysis = analyze_prices(prices)
        if analysis:
            st.subheader("🧠 AI Recommendation:")
            st.write(analysis)
    else:
        st.warning("No prices found.")
