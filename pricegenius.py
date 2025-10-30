import streamlit as st
import requests
import pandas as pd
import pydeck as pdk

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="hellaCheap 🛍️", page_icon="🛒", layout="wide")

SERP_API_KEY = st.secrets.get("SERPAPI_KEY", None)
if not SERP_API_KEY:
    st.warning("⚠️ Missing SERPAPI_KEY. Add it to your Streamlit secrets.")
    st.stop()

# Bay Area tax rates by city
BAY_AREA_TAX = {
    "San Francisco": 9.5,
    "Oakland": 10.25,
    "Berkeley": 10.25,
    "San Jose": 9.375,
    "Palo Alto": 9.125,
    "Fremont": 9.25,
    "Mountain View": 9.125,
    "Santa Clara": 9.125,
    "Daly City": 9.875,
    "All Bay Area": 9.5
}

# Approximate coordinates for main cities (for map plotting)
CITY_COORDS = {
    "San Francisco": [37.7749, -122.4194],
    "Oakland": [37.8044, -122.2712],
    "Berkeley": [37.8715, -122.2730],
    "San Jose": [37.3382, -121.8863],
    "Palo Alto": [37.4419, -122.1430],
    "Fremont": [37.5483, -121.9886],
    "Mountain View": [37.3861, -122.0839],
    "Santa Clara": [37.3541, -121.9552],
    "Daly City": [37.6879, -122.4702]
}

LOCAL_STORES = [
    "Safeway", "CVS", "Rainbow Grocery", "Mollie Stone’s",
    "Bi-Rite Market", "The Epicurean Trader", "Gus’s Market",
    "The Good Life Grocery", "Le Beau Market", "Luke’s Local",
    "Woodlands Market", "Jai Ho Indian Grocery", "22nd and Irving Market"
]

# ----------------------------
# HEADER
# ----------------------------
st.title("🛒 hellaCheap — Real Bay Area Prices")
st.caption("Find real Bay Area prices — from SF corner stores to big-box retailers. ✨")

st.info("Results come from public listings via SerpAPI. Some stores may repeat — often because of bundles, sellers, or stock differences. Only the lowest price per store is shown.")

# ----------------------------
# INPUTS
# ----------------------------
col1, col2 = st.columns([1.2, 1])
with col1:
    city = st.selectbox("Select your Bay Area city:", list(BAY_AREA_TAX.keys()))
with col2:
    query = st.text_input("Search for a product (e.g., AirPods Pro, oat milk, PS5):", "")

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a product name to search.")
        st.stop()

    st.subheader(f"💰 All Bay Area Prices (including tax)")
    tax_rate = BAY_AREA_TAX.get(city, 9.5)
    st.caption(f"Tax rate applied: {tax_rate}%")

    # ----------------------------
    # SERP API CALL
    # ----------------------------
    params = {
        "engine": "google_shopping",
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": SERP_API_KEY
    }

    resp = requests.get("https://serpapi.com/search.json", params=params)
    data = resp.json()

    results = []
    seen_stores = {}

    for item in data.get("shopping_results", []):
        title = item.get("title", "N/A")
        price_str = item.get("price", "").replace("$", "").replace(",", "")
        link = item.get("link", "#")
        source = item.get("source", "N/A")
        thumbnail = item.get("thumbnail", "")
        domain = item.get("domain", "")
        try:
            price = float(price_str)
        except:
            continue

        # Only keep lowest price per store
        if source not in seen_stores or price < seen_stores[source]["price"]:
            seen_stores[source] = {
                "title": title,
                "price": price,
                "link": link,
                "thumbnail": thumbnail,
                "domain": domain
            }

    results = [
        {"store": k, **v, "price_with_tax": round(v["price"] * (1 + tax_rate / 100), 2), "tax_rate": tax_rate}
        for k, v in seen_stores.items()
    ]

    if not results:
        st.warning("No results found. Try a more specific product name.")
        st.stop()

    # ----------------------------
    # DISPLAY RESULTS
    # ----------------------------
    for r in results:
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                st.image(r["thumbnail"], width=180)
            with cols[1]:
                st.markdown(f"### **{r['title']}**")
                st.markdown(f"**{r['store']}** — ${r['price']:.2f}")
                st.markdown(f"**Total after tax:** ${r['price_with_tax']:.2f}")
                st.markdown(f"[🔗 View product on {r['store']}]({r['link']})")

    # ----------------------------
    # DATA TABLE
    # ----------------------------
    df = pd.DataFrame(results)
    st.subheader("📊 Data Table")
    st.dataframe(df[["store", "title", "price", "price_with_tax", "tax_rate", "domain", "link"]])

    # ----------------------------
    # MAP
    # ----------------------------
    st.subheader("🗺️ Local Stores Map (Bay Area)")

    map_data = pd.DataFrame([
        {"store": s, "price": r["price"], "lat": CITY_COORDS.get(city, [37.7749, -122.4194])[0],
         "lon": CITY_COORDS.get(city, [37.7749, -122.4194])[1]}
        for s, r in seen_stores.items()
    ])

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=pdk.ViewState(
            latitude=37.7749,
            longitude=-122.4194,
            zoom=10,
            pitch=0,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=map_data,
                get_position='[lon, lat]',
                get_fill_color='[255, 100, 100, 180]',
                get_radius=500,
                pickable=True,
            )
        ],
        tooltip={"text": "{store}\nPrice: ${price}"}
    ))

# ----------------------------
# FOOTER
# ----------------------------
st.markdown("---")
st.caption("Built with ❤️ in the Bay by hellaCheap — powered by Streamlit + SerpAPI + local love 🌉")
