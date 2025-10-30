import os
import requests
import streamlit as st
from openai import OpenAI
from serpapi import GoogleSearch

# --- Load API Keys ---
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SERPAPI_KEY:
    st.error("❌ Missing SERPAPI_KEY in environment variables.")
if not OPENAI_API_KEY:
    st.error("❌ Missing OPENAI_API_KEY in environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- Streamlit UI ---
st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")
st.title("🛫 PricePilot")
st.caption("Compare live prices across Amazon, Walmart, Best Buy, and more — powered by AI.")

product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

# --- Helper: Normalize store names ---
def clean_store_name(name):
    if not name:
        return "Unknown"
    name = name.lower()
    if "ebay" in name:
        return "eBay"
    if "walmart" in name:
        return "Walmart"
    if "best" in name and "buy" in name:
        return "Best Buy"
    if "apple" in name:
        return "Apple"
    if "amazon" in name:
        return "Amazon"
    return name.title()

# --- Fetch prices ---
def fetch_prices(product_name):
    params = {
        "engine": "google_shopping",
        "q": product_name,
        "api_key": SERPAPI_KEY,
        "num": 30
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    items = results.get("shopping_results", [])
    if not items:
        return []

    store_prices = {}
    for item in items:
        title = item.get("title", "")
        link = item.get("link", "")
        source = clean_store_name(item.get("source", "Unknown"))
        thumbnail = item.get("thumbnail", "")
        price_str = item.get("price", "$0").replace("$", "").replace(",", "")

        try:
            price = float(price_str)
        except ValueError:
            continue

        # Keep only the lowest price per store
        if source not in store_prices or price < store_prices[source]["price"]:
            store_prices[source] = {
                "title": title,
                "price": price,
                "link": link,
                "thumbnail": thumbnail
            }

    return store_prices

# --- Analyze prices ---
def analyze_prices(prices):
    if not prices:
        return "No prices found."

    prompt = "Compare the following product prices and recommend the best value:\n\n"
    for store, data in prices.items():
        prompt += f"{store}: ${data['price']}\n"
    prompt += "\nReturn a short, friendly summary with your recommendation."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({e})"

# --- Display results ---
if product:
    with st.spinner("Fetching live prices..."):
        prices = fetch_prices(product)

    if prices:
        # Sort by price (ascending)
        sorted_prices = dict(sorted(prices.items(), key=lambda x: x[1]['price']))

        st.subheader("💰 Price Results")
        for store, data in sorted_prices.items():
            col1, col2 = st.columns([1, 3])
            with col1:
                if data["thumbnail"]:
                    st.image(data["thumbnail"], width=100)
                else:
                    st.write("🖼️ N/A")
            with col2:
                st.markdown(f"**{store}** — **${data['price']:.2f}**")
                if data["link"]:
                    st.markdown(f"[🌐 View Product]({data['link']})")
                else:
                    st.markdown("No link available")
                st.caption(data["title"])

        st.subheader("🧠 AI Recommendation")
        st.write(analyze_prices(prices))
    else:
        st.warning("No results found. Try another product name.")

st.markdown("---")
st.caption("Built with ❤️ by Team PricePilot — powered by Streamlit, SerpAPI, and OpenAI.")
