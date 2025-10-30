import os
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# ===============================
# 🔐 Load environment variables
# ===============================
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not SERPAPI_KEY or not OPENAI_KEY:
    st.error("⚠️ Missing API keys! Please set SERPAPI_KEY and OPENAI_API_KEY in .env or Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=OPENAI_KEY)

# ===============================
# 🏙 Bay Area Sales Tax Rates
# ===============================
bay_area_tax = {
    "San Francisco": 0.09625,
    "Oakland": 0.105,
    "San Jose": 0.0925,
    "Berkeley": 0.1075,
    "Palo Alto": 0.0925,
    "Fremont": 0.1025,
    "Sunnyvale": 0.0925,
}

# ===============================
# 🎨 Streamlit App UI
# ===============================
st.set_page_config(page_title="HellaCheap SF 🛍️", layout="wide")
st.title("🛒 HellaCheap SF")
st.caption("Compare local prices across Bay Area stores — powered by SerpAPI and OpenAI 💡")

st.markdown(
    """
    Results come from public shopping listings via **SerpAPI**.  
    Some stores may repeat — often because of **bundles, resellers, or stock differences**.  
    We show **only one lowest-priced listing per store**.
    """
)

# City selector
selected_city = st.selectbox("Select your Bay Area city:", list(bay_area_tax.keys()), index=0)
tax_rate = bay_area_tax[selected_city]
st.write(f"💸 *Tax rate applied: {tax_rate * 100:.3f}%*")

# Product input
query = st.text_input("Search any product (e.g., AirPods Pro, oat milk, PS5):")

# ===============================
# 🔍 SerpAPI Search
# ===============================
def fetch_prices_from_serpapi(query):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error("❌ Error fetching data from SerpAPI.")
        return []

    data = response.json()
    if "shopping_results" not in data:
        st.warning("No shopping results found for this query.")
        return []

    # Keep only the lowest price per store
    store_min_prices = {}
    for item in data["shopping_results"]:
        store = item.get("source", "Unknown Store")
        price_str = item.get("price")
        link = item.get("link")
        title = item.get("title")
        thumbnail = item.get("thumbnail")

        if not price_str or "$" not in price_str:
            continue
        try:
            price = float(price_str.replace("$", "").replace(",", "").strip())
        except ValueError:
            continue

        if store not in store_min_prices or price < store_min_prices[store]["price"]:
            store_min_prices[store] = {
                "title": title,
                "store": store,
                "price": price,
                "link": link if link and link.startswith("http") else None,
                "thumbnail": thumbnail,
            }

    return list(store_min_prices.values())

# ===============================
# 🧠 AI Recommendation
# ===============================
def get_ai_summary(prices, city, tax_rate):
    try:
        summary_prompt = f"""
        You are helping a user in {city} compare product prices. 
        Here are the available store prices (before tax):
        {prices}
        The city’s tax rate is {tax_rate*100:.2f}%.
        Identify the lowest-priced option, calculate its final price after tax, 
        and give a friendly 2-3 sentence recommendation about where to buy and why.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI summary unavailable ({e})"

# ===============================
# 📊 Run Search
# ===============================
if query:
    with st.spinner("Fetching live prices..."):
        results = fetch_prices_from_serpapi(query)

    if results:
        df = pd.DataFrame(results)
        st.subheader(f"💰 {selected_city} Prices (including tax)")
        st.write(f"Tax rate applied: **{tax_rate*100:.3f}%**")

        for idx, row in df.iterrows():
            total_price = row["price"] * (1 + tax_rate)
            st.markdown(f"### {row['title']}")
            cols = st.columns([1, 3])
            with cols[0]:
                if row["thumbnail"]:
                    st.image(row["thumbnail"], use_container_width=True)
            with cols[1]:
                st.markdown(f"**{row['store']}** — ${row['price']:.2f}")
                st.markdown(f"**Total after tax:** ${total_price:.2f}")
                if row["link"]:
                    short_link = f"https://www.google.com/maps/search/?api=1&query={row['store'].replace(' ', '+')}"
                    st.markdown(f"[🛒 View Product]({row['link']}) | [📍 Store Location]({short_link})")
                else:
                    st.markdown("_No product link available_")

        # AI Recommendation
        ai_summary = get_ai_summary(df[["store", "price"]].to_dict(orient="records"), selected_city, tax_rate)
        st.subheader("🧠 AI Recommendation")
        st.write(ai_summary)

    else:
        st.warning("No results found. Try another search term.")
else:
    st.info("👆 Enter a product name above to start searching!")
