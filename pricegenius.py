# pricegenius.py
import os
import re
import time
import math
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlparse

# =========================
# Config & Constants
# =========================
APP_NAME = "hellaCheap"
TAGLINE = "Find real prices across big-box, pharmacies, and beloved SF locals — in seconds."

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Sales tax by state (approximate statewide rates; local add-ons vary)
STATE_TAX = {
    "AL": 4.00, "AK": 0.00, "AZ": 5.60, "AR": 6.50, "CA": 7.25, "CO": 2.90,
    "CT": 6.35, "DE": 0.00, "DC": 6.00, "FL": 6.00, "GA": 4.00, "HI": 4.00,
    "ID": 6.00, "IL": 6.25, "IN": 7.00, "IA": 6.00, "KS": 6.50, "KY": 6.00,
    "LA": 4.45, "ME": 5.50, "MD": 6.00, "MA": 6.25, "MI": 6.00, "MN": 6.875,
    "MS": 7.00, "MO": 4.225, "MT": 0.00, "NE": 5.50, "NV": 6.85, "NH": 0.00,
    "NJ": 6.625, "NM": 5.125, "NY": 4.00, "NC": 4.75, "ND": 5.00, "OH": 5.75,
    "OK": 4.50, "OR": 0.00, "PA": 6.00, "RI": 7.00, "SC": 6.00, "SD": 4.50,
    "TN": 7.00, "TX": 6.25, "UT": 6.10, "VT": 6.00, "VA": 5.30, "WA": 6.50,
    "WV": 6.00, "WI": 5.00, "WY": 4.00,
}

# Known physical stores (for pickup-likely heuristic)
PHYSICAL_STORES = {
    "Best Buy", "Walmart", "Target", "Apple", "Costco", "Safeway", "CVS",
    "Bi-Rite Market", "Gus's Market", "The Good Life Grocery", "Le Beau Market",
    "Rainbow Grocery", "22nd and Irving Market", "Woodlands Market",
    "The Epicurean Trader", "Luke’s Local", "Luke's Local", "Jai Ho Indian Grocery",
    "GameStop", "Whatnot"  # Whatnot is online marketplace; leave in list to classify later
}

# Local SF stores & coordinates for map (subset; you can add more later)
BAY_AREA_STORES = {
    "Safeway": [
        ("Safeway - Market St", 37.77383, -122.41942),
        ("Safeway - Marina", 37.80432, -122.43792),
        ("Safeway - Castro", 37.76449, -122.43557),
    ],
    "CVS": [
        ("CVS - Market St", 37.78232, -122.40912),
        ("CVS - Geary Blvd", 37.78326, -122.46271),
        ("CVS - Mission", 37.75210, -122.41890),
    ],
    "Rainbow Grocery": [("Rainbow Grocery Cooperative", 37.76844, -122.41057)],
    "Bi-Rite Market": [
        ("Bi-Rite - 18th St", 37.76162, -122.42542),
        ("Bi-Rite - Divisadero", 37.77405, -122.43772),
    ],
    "Gus's Market": [
        ("Gus’s - Mission", 37.75726, -122.42157),
        ("Gus’s - Haight", 37.76998, -122.44606),
        ("Gus’s - Noriega", 37.75441, -122.48432),
    ],
    "The Good Life Grocery": [
        ("Good Life - Bernal", 37.74375, -122.41392),
        ("Good Life - Potrero", 37.75962, -122.39733),
    ],
    "Le Beau Market": [("Le Beau Market - Nob Hill", 37.79384, -122.41473)],
    "22nd and Irving Market": [("22nd & Irving Market", 37.76357, -122.48168)],
    "Woodlands Market": [
        ("Woodlands - Presidio", 37.79981, -122.45267),
        ("Woodlands - Kentfield", 37.94961, -122.54942),
    ],
    "The Epicurean Trader": [
        ("Epicurean Trader - Hayes", 37.77630, -122.42347),
        ("Epicurean Trader - Ferry", 37.79563, -122.39329),
    ],
    "Luke’s Local": [
        ("Luke’s Local - Cole Valley", 37.76625, -122.45009),
        ("Luke’s Local - Cow Hollow", 37.80012, -122.43674),
    ],
    "Jai Ho Indian Grocery": [("Jai Ho Indian Grocery - SF", 37.76532, -122.42102)],
    "Costco": [
        ("Costco - SF", 37.76813, -122.40418),
        ("Costco - SSF", 37.65580, -122.40775),
    ],
    "Walmart": [
        ("Walmart - San Leandro", 37.72790, -122.17500),
        ("Walmart - Richmond", 37.93510, -122.34760),
    ],
    "Target": [
        ("Target - SF Folsom", 37.77869, -122.40680),
        ("Target - Geary", 37.78320, -122.43140),
    ],
    "Best Buy": [
        ("Best Buy - SF", 37.77240, -122.40680),
        ("Best Buy - Colma", 37.67650, -122.46370),
    ],
    "Apple": [
        ("Apple Union Square", 37.78799, -122.40744),
        ("Apple Chestnut St", 37.80045, -122.43802),
    ],
}

LOCAL_STORE_NAMES = set(BAY_AREA_STORES.keys())

# Normalize store names to a canonical form (keeps simple)
def normalize_store(store: str) -> str:
    if not store:
        return "Unknown"
    s = store.strip()
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    return s

def parse_domain(link: str) -> str:
    try:
        netloc = urlparse(link).netloc
        return netloc.replace("www.", "") if netloc else "unknown"
    except Exception:
        return "unknown"

def price_to_float(p):
    if p is None:
        return None
    if isinstance(p, (int, float)):
        return float(p)
    s = str(p)
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s.replace(",", ""))
    return float(m.group(1)) if m else None

def likely_pickup(store_name: str) -> bool:
    store = normalize_store(store_name)
    # If it's one of our known physicals, likely yes
    if store in PHYSICAL_STORES or store in LOCAL_STORE_NAMES:
        # Special-case Whatnot (mostly online)
        return store not in {"Whatnot"}
    # If domain suggests marketplace, no pickup
    return False

# =========================
# SERPAPI search (+ cache)
# =========================
@st.cache_data(ttl=1800, show_spinner=False)
def google_shopping(query: str, num_results: int = 24) -> list[dict]:
    """Call SerpAPI Google Shopping and return raw item list."""
    if not SERPAPI_KEY:
        return []

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "gl": "us",
        "num": num_results,
    }

    r = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    if r.status_code != 200:
        return []

    data = r.json()
    return data.get("shopping_results", []) or []

def to_clean_items(raw_items: list[dict]) -> list[dict]:
    """Map SerpAPI items to clean structure and drop broken rows."""
    cleaned = []
    for it in raw_items:
        title = it.get("title")
        store = it.get("source")
        price = price_to_float(it.get("extracted_price") or it.get("price"))
        link = it.get("link") or it.get("product_link")
        thumb = None

        # Try thumbnails in a few places
        if it.get("thumbnail"):
            thumb = it["thumbnail"]
        elif it.get("product_photos"):
            if isinstance(it["product_photos"], list) and it["product_photos"]:
                thumb = it["product_photos"][0].get("thumbnail") or it["product_photos"][0].get("link")

        if not (title and store and price and link):
            continue

        cleaned.append({
            "store": normalize_store(store),
            "title": title,
            "price": round(price, 2),
            "link": link,
            "domain": parse_domain(link),
            "thumb": thumb,
        })
    return cleaned

def dedupe_keep_lowest_by_store(items: list[dict]) -> list[dict]:
    """For each store, keep the lowest priced item; prefer merchant links."""
    by_store = {}
    for x in items:
        key = normalize_store(x["store"])
        prev = by_store.get(key)
        if prev is None or x["price"] < prev["price"]:
            by_store[key] = x
        # Prefer direct merchant domain over google.com if prices tie
        elif prev and math.isclose(x["price"], prev["price"], rel_tol=1e-3):
            if prev["domain"] == "google.com" and x["domain"] != "google.com":
                by_store[key] = x
    return sorted(by_store.values(), key=lambda r: r["price"])

def filter_local_sf(items: list[dict], enabled: bool) -> list[dict]:
    if not enabled:
        return items
    keep = []
    for x in items:
        if normalize_store(x["store"]) in LOCAL_STORE_NAMES:
            keep.append(x)
    return keep

def add_tax(items: list[dict], state_abbr: str) -> list[dict]:
    rate = STATE_TAX.get(state_abbr, 0.0) / 100.0
    out = []
    for x in items:
        total = round(x["price"] * (1 + rate), 2)
        out.append({**x, "state_tax_pct": round(rate * 100, 2), "price_with_tax": total})
    return out

# =========================
# UI
# =========================
st.set_page_config(page_title=APP_NAME, page_icon="🛫", layout="wide")

left, mid, right = st.columns([1, 2, 1])
with mid:
    st.markdown(f"### 🛫 {APP_NAME}")
    st.caption(TAGLINE)

st.info(
    "Prices, availability, and vendors are pulled from public shopping feeds via SerpAPI. "
    "Sometimes a merchant appears multiple times due to different sellers, bundles, or conditions. "
    "We keep **one lowest-price listing per store** to reduce duplication."
)

with st.sidebar:
    st.subheader("Settings")
    state = st.selectbox(
        "Calculate total with state tax",
        options=sorted(STATE_TAX.keys()),
        index=sorted(STATE_TAX.keys()).index("CA"),
        help="This uses statewide averages; local add-ons may vary."
    )
    local_mode = st.toggle("🗺️ Local SF Mode (filter to Bay Area favorites)", value=False)
    show_map = st.toggle("Show store map (local mode)", value=False)

st.write("")

query = st.text_input("Enter any product (e.g., “AirPods Pro 2”, “laptop backpack”, “passport photo”):", "")
search_btn = st.button("Search", type="primary")

if search_btn and not query.strip():
    st.warning("Type something to search 🙂")

if query.strip():
    with st.spinner("Searching live prices…"):
        raw = google_shopping(query.strip())
        items = to_clean_items(raw)
        items = dedupe_keep_lowest_by_store(items)
        items = filter_local_sf(items, local_mode)
        items = add_tax(items, state)

    if not items:
        st.warning("No results found. Try a more specific term (e.g., model number) or turn off Local SF Mode.")
    else:
        # Grid of cards
        st.subheader("💰 Price Results")
        cols = st.columns(3, gap="large")
        for i, row in enumerate(items):
            with cols[i % 3]:
                with st.container(border=True):
                    if row.get("thumb"):
                        st.image(row["thumb"], use_container_width=True)
                    st.markdown(f"**{row['title']}**")
                    st.markdown(f"**{row['store']}** — ${row['price']:.2f} (before tax)")
                    st.caption(f"Est. total in {state}: **${row['price_with_tax']:.2f}** @ {row['state_tax_pct']:.2f}%")
                    dom = row.get("domain") or "unknown"
                    st.caption(f"Source: {dom}")

                    # Make sure links are absolute and open in new tab
                    url = row["link"]
                    if not (url.startswith("http://") or url.startswith("https://")):
                        url = "https://" + url

                    st.markdown(
                        f'<a href="{url}" target="_blank" rel="noopener noreferrer">🔗 Buy from {row["store"]}</a>',
                        unsafe_allow_html=True
                    )
                    st.caption("Pickup likely: " + ("✅ Yes" if likely_pickup(row["store"]) else "🛒 Online"))

        # Data table view
        st.write("")
        st.markdown("#### Table View")
        df = pd.DataFrame(items)[["store", "title", "price", "price_with_tax", "state_tax_pct", "domain", "link"]]
        st.dataframe(df, use_container_width=True)

    # Local SF map (optional)
    if local_mode and show_map:
        st.write("")
        st.subheader("🗺️ Local Store Map (Bay Area)")
        rows = []
        for store, locations in BAY_AREA_STORES.items():
            for name, lat, lon in locations:
                rows.append({"store": store, "location": name, "lat": lat, "lon": lon})
        if rows:
            map_df = pd.DataFrame(rows)
            st.map(map_df.rename(columns={"lat": "latitude", "lon": "longitude"}), use_container_width=True)

st.markdown("---")
st.caption("Built with ❤️ in the Bay by hellaCheap — powered by Streamlit + SerpAPI. "
           "We don’t guarantee accuracy; always check the final merchant page for the current price & tax.")
