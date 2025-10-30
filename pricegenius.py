import os
import json
import requests
import streamlit as st
from openai import OpenAI

# --- API Keys ---
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Initialize OpenAI client ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Streamlit app ---
st.title("🛫 PricePilot")
st.write("Compare live prices across BestBuy, Walmart, and Google Shopping.")

# --- Function to fetch prices using SerpAPI ---
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
            "store": item.get("source"),
            "price": item.get("extracted_price"),
            "link": item.get("link")
        })
    return results

# --- Function to analyze prices using OpenAI ---
def analyze_prices(prices):
    if not OPENAI_API_KEY:
        return "❌ Missing OPENAI_API_KEY. Please add it in Streamlit secrets."

    summary_prompt = f"""
    You are a shopping analyst. Given this list of prices, determine which store offers the best deal.
    Suggest whether the user should buy online or in person.
    Here’s the data:
    {json.dumps(prices, indent=2)}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({str(e)[:80]}...)"

# --- UI Input ---
product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

if st.button("🔍 Search"):
    if not product:
        st.warning("Please enter a product name.")
    else:
        with st.spinner("Fetching live prices..."):
            prices = fetch_prices(product)

        if prices:
            st.subheader("💰 Price Results")
            st.json(prices)

            with st.spinner("Analyzing best deal with AI..."):
                analysis = analyze_prices(prices)

            st.subheader("🧠 AI Recommendation")
            st.write(analysis)
        else:
            st.error("No results found. Try another product name.")

# --- Footer ---
st.markdown("---")
st.caption("Built with ❤️ using SerpAPI + OpenAI + Streamlit by @srodrift")
