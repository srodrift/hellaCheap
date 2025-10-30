import os
import requests
import streamlit as st
from openai import OpenAI
import pandas as pd

# --- Initialize API Keys ---
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Initialize OpenAI client ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Streamlit UI setup ---
st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")
st.title("🛫 PricePilot")
st.caption("Compare live prices across BestBuy, Walmart, and Google Shopping.")

# --- Fetch prices function ---
def fetch_prices(product):
    if not SERPAPI_KEY:
        st.error("Missing SERPAPI_KEY environment variable.")
        return []
    
    url = f"https://serpapi.com/search.json?q={product}&engine=google_shopping&api_key={SERPAPI_KEY}"
    response = requests.get(url)
    data = response.json()
    results = []

    for item in data.get("shopping_results", [])[:5]:
        results.append({
            "Product": item.get("title"),
            "Store": item.get("source"),
            "Price ($)": item.get("extracted_price"),
            "Link": item.get("link") or f"https://www.google.com/search?q={product}"
        })

    return results

# --- AI analysis function ---
def analyze_prices(prices):
    if not prices:
        return "No prices found to analyze."

    summary_prompt = (
        "You are a smart shopping assistant. Given the following list of prices, "
        "identify which store offers the best deal, and give a short recommendation.\n\n"
        f"{prices}\n\n"
        "Return your response in a friendly, concise tone."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI analysis unavailable: {str(e)}"

# --- UI Interaction ---
product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

if product:
    with st.spinner("Fetching live prices..."):
        prices = fetch_prices(product)

    if prices:
        # Display DataFrame with clickable links
        df = pd.DataFrame(prices)
        st.subheader("💰 Price Results")
        def make_clickable(val):
            return f'<a href="{val}" target="_blank">🔗 Link</a>'
        df["Link"] = df["Link"].apply(make_clickable)
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # 🏆 Highlight best deal
        best_deal = min(prices, key=lambda x: x["Price ($)"] or float("inf"))
        st.markdown(
            f"""
            <div style="background-color:#d1fae5;padding:15px;border-radius:10px;margin-top:20px;">
                <h4>🏆 Best Deal: {best_deal['Store']}</h4>
                <b>{best_deal['Product']}</b><br>
                💵 ${best_deal['Price ($)']}<br>
                <a href="{best_deal['Link']}" target="_blank">View on store →</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # AI recommendation
        with st.spinner("Analyzing deals..."):
            analysis = analyze_prices(prices)
        st.subheader("🧠 AI Recommendation")
        st.write(analysis)
    else:
        st.warning("No results found.")
