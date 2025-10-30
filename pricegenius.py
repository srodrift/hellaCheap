import streamlit as st
import requests
import pandas as pd

# ---- CONFIG ----
SERPAPI_KEY = "c13a5777ffd1fb6787bd1a2f33d01eb38102d0a7d673f8d6ac10ba093c275e04"

st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")

# ---- HEADER ----
st.markdown(
    """
    <h1 style='text-align: center;'>🛫 <b>PricePilot</b></h1>
    <p style='text-align: center; color: gray;'>
    Compare live prices across BestBuy, Walmart, eBay, and more — powered by AI.
    </p>
    """,
    unsafe_allow_html=True
)

# ---- USER INPUTS ----
product_name = st.text_input("Enter a product name (e.g. AirPods Pro 2):")
filter_terms_input = st.text_input(
    "Optional: must include these words (comma-separated, e.g. San Francisco, 2024, paperback):"
)

# Convert filters into a list
filter_terms = [term.strip().lower() for term in filter_terms_input.split(",") if term.strip()]

# ---- FUNCTION TO FETCH PRICES ----
def fetch_prices(product_name):
    url = "https://serpapi.com/search.json"
    params = {"engine": "google_shopping", "q": product_name, "api_key": SERPAPI_KEY}
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
            title = item.get("title") or ""

            if not price_str:
                continue

            try:
                price = float("".join(ch for ch in price_str if ch.isdigit() or ch == "."))
            except:
                continue

            # Fallback link
            if not link or not link.startswith("http"):
                link = f"https://www.google.com/search?q={product_name.replace(' ', '+')}+buy"

            # Apply multiple filter terms
            if filter_terms and not all(term in title.lower() for term in filter_terms):
                continue

            # Keep only lowest per store
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
if product_name:
    st.subheader("💰 Price Results")
    prices = fetch_prices(product_name)

    if not prices:
        st.warning("No prices found matching your query. Try adjusting the filters.")
    else:
        df = pd.DataFrame(prices)
        for _, row in df.iterrows():
            col1, col2 = st.columns([1, 3])
            with col1:
                if row["thumbnail"]:
                    st.image(row["thumbnail"], width=80)
            with col2:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 12px;">
                        <b>{row['store']}</b> — <span style="color:green;">${row['price']:.2f}</span>
                        <a href="{row['link']}" target="_blank" style="margin-left:10px;">🌐 View Product</a><br>
                        <span style="font-size:14px; color:gray;">{row['title']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ---- AI Recommendation ----
        best = min(prices, key=lambda x: x["price"])
        st.markdown("### 🧠 AI Recommendation")
        st.markdown(
            f"""
            <div style="background-color:#e8fce8; padding:12px; border-radius:10px;">
            The best deal is from <b>{best['store']}</b> at 
            <span style="color:green;">${best['price']:.2f}</span>! 
            <a href="{best['link']}" target="_blank">Buy from here</a> for the best price. 🛍️
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("<hr><center>Built with ❤️ by Team PricePilot — powered by Streamlit & SerpAPI</center>", unsafe_allow_html=True)
