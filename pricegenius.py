import streamlit as st
import requests
import pandas as pd

# ---- CONFIG ----
SERPAPI_KEY = "c13a5777ffd1fb6787bd1a2f33d01eb38102d0a7d673f8d6ac10ba093c275e04"  # your key

st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")

# ---- HEADER ----
st.title("🛫 PricePilot")
st.caption("Compare live prices across BestBuy, Walmart, eBay, and more — powered by AI.")

query = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

# ---- FUNCTION TO FETCH PRICES ----
def fetch_prices(product_name):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": product_name,
        "api_key": SERPAPI_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()

    prices = []
    seen_stores = {}

    if "shopping_results" in data:
        for item in data["shopping_results"]:
            store = item.get("source") or item.get("seller") or "Unknown"
            price_str = item.get("price")
            link = item.get("link")
            thumbnail = item.get("thumbnail")
            title = item.get("title")

            # Skip if no price
            if not price_str:
                continue

            # Convert to float
            price = None
            try:
                price = float("".join(ch for ch in price_str if ch.isdigit() or ch == "."))
            except:
                continue

            # Keep only lowest price per store
            if store not in seen_stores or price < seen_stores[store]["price"]:
                seen_stores[store] = {
                    "store": store,
                    "price": price,
                    "link": link,
                    "thumbnail": thumbnail,
                    "title": title
                }

        prices = list(seen_stores.values())

    return prices

# ---- DISPLAY RESULTS ----
if query:
    st.subheader("💰 Price Results")
    prices = fetch_prices(query)

    if not prices:
        st.warning("No prices found. Try another product name.")
    else:
        df = pd.DataFrame(prices)
        for _, row in df.iterrows():
            col1, col2 = st.columns([1, 3])
            with col1:
                if row["thumbnail"]:
                    st.image(row["thumbnail"], width=80)
            with col2:
                store_link = row["link"] if row["link"] else "#"
                st.markdown(
                    f"**{row['store']}** — ${row['price']:.2f}  🌐 [View Product]({store_link})  \n{row['title']}",
                    unsafe_allow_html=True
                )

        # ---- RECOMMENDATION ----
        best = min(prices, key=lambda x: x["price"])
        st.markdown("### 🧠 AI Recommendation")
        st.success(
            f"The best deal is from **{best['store']}** at **${best['price']:.2f}**! "
            f"Buy from [here]({best['link']}) for the best price. 🛍️"
        )

st.markdown("---")
st.caption("Built with ❤️ by Team PricePilot — powered by Streamlit and SerpAPI")
