# pricegenius.py — hellaCheap Bay Area Edition 🌉

import os
import re
import math
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlparse

APP_NAME = "hellaCheap"
TAGLINE = "Find real Bay Area prices — from SF staples to big-box stores."

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# ✅ Bay Area Tax Rates (2025)
BAY_TAX = {
    "San Francisco": 8.625,
    "Oakland": 10.25,
    "Berkeley": 10.25,
    "San Jose": 9.375,
    "Fremont": 10.25,
    "San Mateo": 9.625,
    "Marin County": 9.0,
    "All Bay Area": 9.5,
}

# ✅ Bay Area Stores (same as before)
BAY_AREA_STORES = {
    "Safeway": [
        ("Safeway - Market St", 37.77383, -122.41942),
        ("Safeway - Marina", 37.80432, -122.43792),
        ("Safeway - Castro", 37.76449, -122.43557),
    ],
    "CVS": [
        ("CVS - Market St", 37.78232, -122.40912),
        ("CVS - Geary Blvd", 37.78326, -122.46271),
    ],
    "Rainbow Grocery": [("Rainbow Grocery Cooperative", 37.76844, -122.41057)],
    "Bi-Rite Market": [
        ("Bi-Rite - 18th St", 37.76162, -122.42542),
        ("Bi-Rite - Divisadero", 37.77405, -122.43772),
    ],
    "Gus's Market": [
        ("Gus’s - Mission", 37.75726, -122.42157),
        ("Gus’s - Haight", 37.76998, -122.44606),
    ],
    "The Good Life Grocery": [
        ("Good Life - Bernal", 37.74375, -122.41392),
        ("Good Life - Potrero", 37.75962, -122.39733),
    ],
    "Le Beau Market": [("Le Beau Market - Nob Hill", 37.79384, -122.41473)],
    "Woodlands Market": [("Woodlands - Presidio", 37.79981, -122.45267)],
    "The Epicurean Trader": [("Epicurean Trader - Hayes", 37.77630, -122.42347)],
    "Luke’s Local": [("Luke’s Local - Cole Valley", 37.76625, -122.45009)],
    "Jai Ho Indian Grocery": [("Jai Ho Indian Grocery - SF", 37.76532, -122.42102)],
    "Costco": [("Costco - SF", 37.76813, -122.40418)],
    "Target": [("Target - SF Folsom", 37.77869, -122.40680)],
    "Best Buy": [("Best Buy - SF", 37.77240, -122.40680)],
    "Apple": [("Apple Union Square", 37.78799, -122.40744)],
    "Walmart": [("Walmart - Richmond", 37.93510, -122.34760)],
}

LOCAL_STORE_NAMES = set(BAY_AREA_STORES.keys())

def normalize_store(store: str) -> str:
    return re.sub(r"\s+", " ", store.strip().replace("’", "'")) if store else "Unknown"

def parse_domain(link: str) -> str:
    try:
        netloc = urlparse(link).netloc
        return netloc.replace("www.", "") or "unknown"
    except:
        return "unknown"

def price_to_float(val):
    if isinstance(val, (int, float)): return float(val)
    if not val: return None
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(val).replace(",", ""))
    return float(m.group(1)) if m else None

@st.cache_data(ttl=1800, show_spinner=False)
def google_shopping(query: str):
    if not SERPAPI_KEY:
        return []
    r = requests.get("https://serpapi.com/search.json", params={
        "engine": "google_shopping", "q": query,
        "api_key": SERPAPI_KEY, "hl": "en", "gl": "us", "num": 20
    })
    if r.status_code != 200: return []
    return r.json().get("shopping_results", [])

def clean_results(raw):
    out = []
    for item in raw:
        store = normalize_store(item.get("source"))
        title = item.get("title")
        link = item.get("link") or item.get("product_link")
        price = price_to_float(item.get("extracted_price") or item.get("price"))
        thumb = item.get("thumbnail")
        if not (store and title and price and link): continue
        out.append({
            "store": store, "title": title,
            "price": round(price, 2), "link": link,
            "domain": parse_domain(link), "thumb": thumb
        })
    return out

def dedupe_lowest(items):
    best = {}
    for x in items:
        s = x["store"]
        if s not in best or x["price"] < best[s]["price"]:
            best[s] = x
    return sorted(best.values(), key=lambda i: i["price"])

def add_tax(items, city):
    rate = BAY_TAX.get(city, 9.5) / 100
    for x in items:
        x["price_with_tax"] = round(x["price"] * (1 + rate), 2)
        x["tax_rate"] = round(rate * 100, 3)
    return items

# ------------------ UI ------------------
st.set_page_config(page_title="hellaCheap", page_icon="🌉", layout="wide")

st.markdown(f"## 🌉 {APP_NAME}")
st.caption(TAGLINE)

st.info(
    "Results come from public shopping listings via SerpAPI. "
    "Some stores may repeat — often because of bundles, different sellers, or stock levels. "
    "We show only one lowest-priced listing per store."
)

city = st.selectbox("Select your Bay Area city:", list(BAY_TAX.keys()), index=0)
query = st.text_input("Search any product (e.g., AirPods Pro, oat milk, PS5):")
search = st.button("Search")

if search and not query.strip():
    st.warning("Enter something to search 🙂")

if query.strip():
    with st.spinner("Looking up Bay Area deals..."):
        raw = google_shopping(query)
        items = clean_results(raw)
        items = dedupe_lowest(items)
        items = add_tax(items, city)
        # Filter to Bay Area stores only
        items = [x for x in items if normalize_store(x["store"]) in LOCAL_STORE_NAMES or x["domain"] not in {"google.com"}]

    if not items:
        st.warning("No Bay Area listings found. Try another term.")
    else:
        st.subheader(f"💰 {city} Prices (including tax)")
        st.caption(f"Tax rate applied: {BAY_TAX[city]}%")

        cols = st.columns(3)
        for i, row in enumerate(items):
            with cols[i % 3]:
                with st.container(border=True):
                    if row.get("thumb"):
                        st.image(row["thumb"], use_container_width=True)
                    st.markdown(f"**{row['title']}**")
                    st.markdown(f"{row['store']} — ${row['price']:.2f}")
                    st.caption(f"Total after tax: ${row['price_with_tax']:.2f}")
                    url = row["link"]
                    if not url.startswith("http"): url = "https://" + url
                    st.markdown(f"[🔗 Buy from {row['store']}]({url})", unsafe_allow_html=True)

        st.markdown("#### Data Table")
        df = pd.DataFrame(items)[["store", "title", "price", "price_with_tax", "tax_rate", "domain", "link"]]
        st.dataframe(df, use_container_width=True)

        # Bay Area Map
        st.write("### 🗺️ Local Stores Map (Bay Area)")
        map_rows = []
        for store, locs in BAY_AREA_STORES.items():
            for name, lat, lon in locs:
                map_rows.append({"store": store, "name": name, "lat": lat, "lon": lon})
        st.map(pd.DataFrame(map_rows).rename(columns={"lat": "latitude", "lon": "longitude"}))

st.markdown("---")
st.caption("Built with ❤️ in the Bay by hellaCheap — powered by Streamlit + SerpAPI + local love 🌉")
