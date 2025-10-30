import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import urllib.parse

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="hellaCheap 🛍️", page_icon="🛒", layout="wide")

SERP_API_KEY = st.secrets.get("SERPAPI_KEY", None)
if not SERP_API_KEY:
    st.warning("⚠️ Missing SERPAPI_KEY. Add it to your Streamlit secrets.")
    st.stop()

# Bay Area city tax rates
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
}

# Coordinates for map centers
CITY_COORDS = {
    "San Francisco": [37.7749, -122.4194],
    "Oakland": [37.8044, -122.2712],
    "Berkeley": [37.8715, -122.2730],
    "San Jose": [37.3382, -121.8863],
    "Palo Alto": [37.4419, -122.1430],
    "Fremont": [37.5483, -121.9886],
    "Mountain View": [37.3861, -122.0839],
    "Santa Clara": [37.3541, -121.9552],
    "Daly City": [37.6879, -122.4702],
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
st.title("🛒 hellaCheap — Bay Area Price Finder")
st.caption("Find real prices across San Francisco & Bay Area stores — from local gems to national chains.")

st.info("💡 Some stores may repeat due to bundles, stock, or multiple sellers. Only the **lowest price per store** is shown.")

# ----------------------------
# USER INPUT
# ----------------------------
col1, col2 = st.columns([1.2, 1])
with col1:
    city = st.selectbox("📍 Choose a Bay Area city:", list(BAY_AREA_TAX.keys()))
with col2:
    query = st.text_input("🔍 Search for a product (e.g. AirPods, oat milk, PS5):", "")

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a product name to search.")
        st.stop()

    st.subheader(f"💰 Prices around {city}")
    tax_rate = BAY_AREA_TAX.get(city, 9.5)
    st.caption(f"Sales tax in {city}: **{tax_rate}%**")

    # ----------------------------
    # FETCH DATA
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

        # Keep only lowest price per store
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
        st.warning("No results found. Try refining your search.")
        st.stop()

    # ----------------------------
    # DISPLAY RESULTS
    # ----------------------------
    for r in results:
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                st.image(r["thumbnail"], width=160)
            with cols[1]:
                st.markdown(f"### **{r['title']}**")
                st.markdown(f"**{r['store']}** — ${r['price']:.2f}")
                st.markdown(f"💵 **With tax:** ${r['price_with_tax']:.2f}")
                st.markdown(f"[🛍️ View on {r['store']}]({r['link']})")

    # ----------------------------
    # TABLE VIEW
    # ----------------------------
    df = pd.DataFrame(results)
    st.subheader("📊 Compare All Stores")
    st.dataframe(df[["store", "title", "price", "price_with_tax", "tax_rate", "link"]])

    # ----------------------------
    # CLICKABLE MAP
    # ----------------------------
    st.subheader("🗺️ Bay Area Store Locations")

    def store_to_map_url(store):
        query = urllib.parse.quote_plus(f"{store}, {city}, California")
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    map_data = pd.DataFrame([
        {
            "store": s,
            "price": r["price"],
            "lat": CITY_COORDS.get(city, [37.7749, -122.4194])[0],
            "lon": CITY_COORDS.get(city, [37.7749, -122.4194])[1],
            "url": store_to_map_url(s)
        }
        for s, r in seen_stores.items()
    ])

    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=pdk.ViewState(
                latitude=CITY_COORDS.get(city, [37.7749, -122.4194])[0],
                longitude=CITY_COORDS.get(city, [37.7749, -122.4194])[1],
                zoom=10,
                pitch=0,
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=map_data,
                    get_position='[lon, lat]',
                    get_fill_color='[255, 80, 80, 200]',
                    get_radius=500,
                    pickable=True,
                )
            ],
            tooltip={
                "html": "<b>{store}</b><br/>Price: ${price}<br/><a href='{url}' target='_blank'>📍 Open in Maps – "
                        + city + "</a>",
                "style": {"backgroundColor": "white", "color": "black"}
            }
        )
    )

# ----------------------------
# FOOTER
# ----------------------------
st.markdown("""
---
<div style='text-align: center; font-size: 15px; color: goldenrod;'>
🌉 Built with ❤️ in <b>San Francisco</b> — <i>by hellaCheap</i><br>
Powered by Streamlit & SerpAPI
</div>
""", unsafe_allow_html=True)