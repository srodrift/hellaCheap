import os
import json
import time
import math
import requests
import pandas as pd
import streamlit as st

# =========================
# Branding
# =========================
st.set_page_config(page_title="hellaCheap — SF price hacks", page_icon="🛍️", layout="wide")

BRAND = "hellaCheap"
TAGLINE = "Born in San Francisco. Built for deal hunters everywhere."
SUB = "Compare live prices across Bay Area & online stores — tax-aware, hyperlocal, and AI-guided."

SERPAPI_KEY = os.getenv("SERPAPI_KEY", st.secrets.get("SERPAPI_KEY", ""))

# =========================
# Bay Area defaults (fallback)
# =========================
BAY_AREA_TAX = {
    "San Francisco": 0.08625,
    "Oakland": 0.1025,
    "San Jose": 0.0925,
    "Berkeley": 0.1025,
    "Daly City": 0.0975,
    "Palo Alto": 0.0925,
}
DEFAULT_CITY = "San Francisco"

# =========================
# Store aliases & pins
# =========================
CHAIN_ALIASES = {
    "best buy": "Best Buy",
    "apple": "Apple",
    "target": "Target",
    "walmart": "Walmart",
    "costco": "Costco",
    "sam's club": "Sam's Club"
}

BAY_AREA_STORES = {
    "Best Buy": [("Best Buy SF - Harrison", 37.7725, -122.4068)],
    "Target": [("Target SF - Mission St", 37.7848, -122.4037)],
    "Walmart": [("Walmart San Leandro", 37.7027, -122.1543)],
    "Costco": [("Costco SF - 10th St", 37.7724, -122.4074)],
    "Apple": [("Apple Union Square", 37.7880, -122.4075)],
}

# =========================
# Helper functions
# =========================
def chain_name(store: str):
    s = (store or "").lower()
    for k, v in CHAIN_ALIASES.items():
        if k in s:
            return v
    return store or "Unknown"

@st.cache_data(ttl=3600)
def cached_serpapi_search(query: str, api_key: str, num_results=20):
    """Cached SerpAPI call"""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": api_key,
        "num": num_results
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def get_sales_tax_by_zip(zip_code: str):
    """Fetch live US tax rate by ZIP (Avalara public API)."""
    try:
        resp = requests.get(f"https://api.salestaxapi.io/api/v1/salestax?country=US&zip={zip_code}", timeout=10)
        data = resp.json()
        rate = data.get("sales_tax", 0.09)
        return float(rate)
    except Exception:
        return BAY_AREA_TAX.get(DEFAULT_CITY, 0.09)

def dedupe_lowest(prices):
    lowest = {}
    for p in prices:
        s = p["store"]
        if s not in lowest or p["price"] < lowest[s]["price"]:
            lowest[s] = p
    return list(lowest.values())

def enrich_totals(prices, tax_rate):
    for p in prices:
        p["price_with_tax"] = round(p["price"] * (1 + tax_rate), 2)
    return prices

def parse_results(data):
    results = []
    for itm in data.get("shopping_results", []):
        store = chain_name(itm.get("source") or itm.get("seller") or "Unknown")
        price = itm.get("extracted_price")
        if not price:
            continue
        link = itm.get("link")
        pickup = False
        shiptext = None
        if itm.get("delivery"):
            shiptext = itm["delivery"]
        elif itm.get("extensions"):
            shiptext = ", ".join(itm["extensions"])
        if shiptext and ("Pickup" in shiptext or "In-store" in shiptext):
            pickup = True
        results.append({
            "title": itm.get("title"),
            "store": store,
            "price": price,
            "link": link,
            "thumbnail": itm.get("thumbnail"),
            "pickup_available": pickup,
            "shipping": shiptext
        })
    return results

# =========================
# UI
# =========================
st.markdown(f"## 🛍️ {BRAND}")
st.caption(TAGLINE)
st.write(SUB)
st.divider()

query = st.text_input("Enter a product name (e.g. AirPods Pro 2)")
zip_code = st.text_input("Enter your ZIP code (for accurate tax rate)", "94103")
search = st.button("Search Deals")

if search:
    if not query.strip():
        st.warning("Enter a product name to search.")
        st.stop()

    tax_rate = get_sales_tax_by_zip(zip_code)
    st.caption(f"Using sales tax rate: {tax_rate*100:.2f}% for ZIP {zip_code}")

    with st.spinner("Fetching deals..."):
        try:
            data = cached_serpapi_search(query, SERPAPI_KEY)
            results = parse_results(data)
        except Exception as e:
            st.error(f"Failed to fetch results: {e}")
            st.stop()

    if not results:
        st.info("No products found for that query.")
        st.stop()

    results = dedupe_lowest(results)
    results = enrich_totals(results, tax_rate)
    st.markdown("### 💰 Price Results")

    for r in sorted(results, key=lambda x: x["price"]):
        with st.container(border=True):
            c1, c2 = st.columns([0.2, 0.8])
            with c1:
                st.image(r["thumbnail"] or "https://placehold.co/200x200?text=No+Image", use_container_width=True)
            with c2:
                st.markdown(f"**{r['store']}** — ${r['price']:.2f}")
                st.markdown(f"[🔗 View Product]({r['link']})", unsafe_allow_html=True)
                if r.get("pickup_available"):
                    st.markdown("🚗 **Pickup available!**")
                elif r.get("shipping"):
                    st.caption(r["shipping"])
                st.caption(f"**Price incl. tax:** ${r['price_with_tax']:.2f}")

    best = min(results, key=lambda x: x["price"])
    st.success(f"🧠 Best Deal: **{best['store']}** — ${best['price']:.2f} ({best['link']})")

    # map
    st.markdown("### 🗺️ Bay Area Store Map")
    rows = []
    for r in results:
        cname = chain_name(r["store"])
        if cname in BAY_AREA_STORES:
            for name, lat, lon in BAY_AREA_STORES[cname]:
                rows.append({"store": name, "lat": lat, "lon": lon})
    if rows:
        st.map(pd.DataFrame(rows), latitude="lat", longitude="lon", size=200)
    else:
        st.info("No Bay Area store pins available for these stores.")

    st.caption(
        "⚠️ Prices and taxes vary by ZIP code and time. Some stores may appear multiple times "
        "due to marketplace listings; we only show the **lowest** per store. Pickup data "
        "comes from SerpAPI extensions and may not always be current."
    )
