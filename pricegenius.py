import os
import math
import json
from collections import defaultdict

import requests
import pandas as pd
import streamlit as st

# --- Optional AI (auto-disables if no key) ---
try:
    from openai import OpenAI
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
except Exception:
    client = None

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# ---------------- UI ----------------
st.set_page_config(page_title="HellaCheap SF Bay", page_icon="🛒", layout="centered")
st.title("🛒 HellaCheap — Bay Area Deals")
st.caption("Compare local-ish prices across Bay Area stores (via Google Shopping/SerpAPI). One lowest listing per store, with city tax.")

if not SERPAPI_KEY:
    st.error("Missing SERPAPI_KEY. Add it to your local .env or Streamlit Cloud secrets.")
    st.stop()

# Bay Area city tax rates (approx, can tweak)
CITY_TAX = {
    "San Francisco": 0.09625,  # 9.625%
    "Oakland":       0.1050,   # 10.50%
    "Berkeley":      0.1075,   # 10.75%
    "San Jose":      0.0925,   # 9.25%
    "Palo Alto":     0.0925,   # 9.25%
    "Fremont":       0.0975,   # 9.75%
}

# Neighborhood/ZIP hints (lightweight, not exhaustive)
# Each store maps to a list of (City, Neighborhood, ZIP)
STORE_AREAS = {
    "Safeway": [
        ("San Francisco", "Mission", "94103"),
        ("San Francisco", "Outer Sunset", "94122"),
        ("Oakland", "Grand Lake", "94610"),
        ("Berkeley", "North Berkeley", "94703"),
        ("San Jose", "Willow Glen", "95125"),
        ("Palo Alto", "Midtown", "94303"),
        ("Fremont", "Irvington", "94538"),
    ],
    "Trader Joe's": [
        ("San Francisco", "Laurel Heights", "94118"),
        ("San Francisco", "SoMa", "94103"),
        ("Berkeley", "Downtown", "94704"),
        ("San Jose", "Stevens Creek", "95129"),
        ("Palo Alto", "California Ave", "94306"),
    ],
    "Target": [
        ("San Francisco", "Mission", "94110"),
        ("San Francisco", "Metreon/SoMa", "94103"),
        ("Oakland", "Eastlake", "94606"),
        ("San Jose", "Blossom Hill", "95123"),
        ("Fremont", "Pacific Commons", "94538"),
    ],
    "Costco": [
        ("San Francisco", "SoMa", "94103"),
        ("South San Francisco", "Oyster Point", "94080"),
        ("San Jose", "North San Jose", "95134"),
        ("Fremont", "Auto Mall", "94538"),
    ],
    "Whole Foods": [
        ("San Francisco", "SoMa", "94105"),
        ("San Francisco", "Noe Valley", "94114"),
        ("Oakland", "Uptown", "94612"),
        ("Berkeley", "Gilman", "94710"),
        ("San Jose", "The Alameda", "95126"),
    ],
    "Walmart": [
        ("San Leandro", "Bayfair", "94578"),
        ("Mountain View", "Showers Dr", "94040"),
        ("San Jose", "Almaden", "95118"),
        ("Fremont", "Warm Springs", "94538"),
    ],
    "Best Buy": [
        ("San Francisco", "SoMa", "94103"),
        ("San Carlos", "Industrial Rd", "94070"),
        ("San Jose", "Stevens Creek", "95129"),
        ("Fremont", "Auto Mall", "94538"),
    ],
    "CVS": [
        ("San Francisco", "Civic Center", "94102"),
        ("San Francisco", "Inner Sunset", "94122"),
        ("Oakland", "Temescal", "94609"),
        ("San Jose", "Downtown", "95112"),
    ],
    "Walgreens": [
        ("San Francisco", "Market St / Union Sq", "94102"),
        ("San Francisco", "Inner Richmond", "94118"),
        ("Berkeley", "Downtown", "94704"),
        ("San Jose", "Willow Glen", "95125"),
    ],
    "H Mart": [
        ("San Francisco", "Oceanview/Daly City edge", "94014"),
        ("San Jose", "Koreatown", "95118"),
        ("San Jose", "North San Jose", "95131"),
    ],
    "99 Ranch": [
        ("Daly City", "Serramonte", "94015"),
        ("Fremont", "Warm Springs", "94538"),
        ("San Jose", "North Valley", "95133"),
    ],
    "Bi-Rite": [
        ("San Francisco", "Mission", "94110"),
        ("San Francisco", "Western Addition", "94117"),
    ],
    "Gus's Market": [
        ("San Francisco", "Mission", "94103"),
        ("San Francisco", "Mission Bay", "94158"),
    ],
    "Rainbow Grocery": [
        ("San Francisco", "Mission", "94103"),
    ],
    "Mollie Stone's": [
        ("San Francisco", "Pacific Heights", "94123"),
        ("Palo Alto", "Midtown", "94303"),
        ("Burlingame", "Broadway", "94010"),
    ],
    "The Good Life Grocery": [
        ("San Francisco", "Bernal Heights", "94110"),
        ("San Francisco", "Potrero Hill", "94107"),
    ],
    "Le Beau Market": [
        ("San Francisco", "Nob Hill", "94109"),
    ],
    "Luke's Local": [
        ("San Francisco", "Cole Valley", "94117"),
        ("San Francisco", "Cow Hollow", "94123"),
    ],
    "Berkeley Bowl": [
        ("Berkeley", "South Berkeley", "94703"),
        ("Berkeley", "West Berkeley", "94710"),
    ],
    "Ranch 99": [  # synonym
        ("Fremont", "Warm Springs", "94538"),
        ("San Jose", "North Valley", "95133"),
    ],
}

BAY_CITIES = list(CITY_TAX.keys())
city = st.selectbox("Select your Bay Area city:", BAY_CITIES, index=0)
tax = CITY_TAX[city]
st.markdown(f"**💸 Tax rate applied:** {round(tax*100, 3)}%")

query = st.text_input("Search any product (e.g., AirPods Pro, oat milk, PS5):", value="okra")
run = st.button("Search")

st.divider()

# --------- helpers ---------

def maps_search_url(store: str, city_name: str):
    # simple & reliable: Google Maps search; no brittle address
    q = f"{store} {city_name}"
    return f"https://www.google.com/maps/search/{requests.utils.quote(q)}"

def infer_area_hint(store: str, city_name: str):
    """Pick a neighborhood/ZIP hint for the store in this city if we have one."""
    entries = STORE_AREAS.get(store) or STORE_AREAS.get(store.replace("’","'")) or []
    candidates = [e for e in entries if e[0] == city_name]
    if candidates:
        # choose a deterministic pick based on hash to keep same result per store
        idx = abs(hash(store + city_name)) % len(candidates)
        _, neighborhood, zipc = candidates[idx]
        return f"{neighborhood}, {zipc}"
    # If we have entries for other cities, show generic ZIP tag for city
    return f"{city_name} area"

def normalize_store(raw_source: str):
    # Clean up noisy source strings like "Walmart - Seller", "eBay - user", etc.
    if not raw_source:
        return "Unknown"
    s = raw_source.strip()
    # Trim seller suffix
    for sep in [" - ", " — "]:
        if sep in s:
            left = s.split(sep, 1)[0].strip()
            if left:
                s = left
                break
    # Unify aliases
    aliases = {
        "Ranch 99": "99 Ranch",
        "99 Ranch Market": "99 Ranch",
        "Hmart": "H Mart",
        "Gus’s Market": "Gus's Market",
        "Gus’ Market": "Gus's Market",
        "Bi Rite": "Bi-Rite",
        "BiRite": "Bi-Rite",
    }
    return aliases.get(s, s)

def fetch_prices(search_term: str):
    """Query SerpAPI's Google Shopping engine and return list of items with fields we care about."""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": search_term,
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY,
        "num": "80",   # get more, we'll dedupe
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    items = []
    for it in data.get("shopping_results", []):
        price = it.get("extracted_price")
        if price is None:
            continue
        source = normalize_store(it.get("source"))
        # Prefer serpapi product link if present; else fall back to raw link
        link = it.get("product_link") or it.get("link")
        title = it.get("title") or search_term
        thumbnail = None
        if "thumbnail" in it:
            thumbnail = it["thumbnail"]
        items.append({
            "title": title,
            "store": source,
            "price": float(price),
            "link": link,
            "thumb": thumbnail
        })
    return items

def choose_lowest_per_store(items):
    """Deduplicate by store, keep the lowest-priced item."""
    best = {}
    for it in items:
        s = it["store"]
        if s not in best or it["price"] < best[s]["price"]:
            best[s] = it
    # Return stable order by price asc
    return sorted(best.values(), key=lambda x: x["price"])

def fmt_money(x):
    return f"${x:,.2f}"

def ai_summary(city_name: str, tax_rate: float, rows: list[dict]):
    """Optional AI summary; falls back to deterministic text if no OpenAI key."""
    if not rows:
        return "No results to analyze."
    cheapest = rows[0]
    price = cheapest["price"]
    total = price * (1 + tax_rate)
    if not client:
        return f"The best price is **{fmt_money(price)}** at **{cheapest['store']}** (≈ {fmt_money(total)} after {round(tax_rate*100,3)}% {city_name} tax)."
    try:
        msg = (
            "You are a concise shopping assistant. "
            "Given the result list (already deduped by store, ascending by price), "
            f"pick the single cheapest and give a one-sentence recommendation. Include city tax {round(tax_rate*100,3)}%.\n\n"
            f"City: {city_name}\n"
            f"Results JSON: {json.dumps(rows[:8], ensure_ascii=False)}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":msg}],
            temperature=0.2,
            max_tokens=120,
        )
        text = resp.choices[0].message.content.strip()
        # sanitize weird newlines that sometimes appear
        text = " ".join(text.split())
        return text
    except Exception:
        return f"The best price is **{fmt_money(price)}** at **{cheapest['store']}** (≈ {fmt_money(total)} after tax)."

# ---------------- Run Search ----------------
st.markdown("> _Results come from public shopping listings via SerpAPI. Stores may repeat because of bundles/resellers/stock; we show the **lowest** price per store._")

if run and query.strip():
    with st.spinner("Searching deals…"):
        raw = fetch_prices(query.strip())
        rows = choose_lowest_per_store(raw)

    st.subheader(f"💰 {city} Prices (including tax)")
    st.caption(f"Tax rate applied: {round(tax*100,3)}%")

    if not rows:
        st.info("No results found. Try a more specific search (e.g., model, size, flavor).")
    else:
        for it in rows:
            store = it["store"]
            title = it["title"]
            price = it["price"]
            total = price * (1 + tax)

            # Area hint
            area_hint = infer_area_hint(store, city)
            maps_url = maps_search_url(store, city)

            # Render card
            with st.container(border=True):
                # Title
                st.markdown(f"### {title}")

                # Thumbnail (small)
                if it.get("thumb"):
                    st.image(it["thumb"], width=120)

                # Store + area
                st.markdown(f"**{store}** — _{area_hint}_")

                # Price & total
                st.markdown(f"**Price:** {fmt_money(price)}")
                st.markdown(f"**Total after tax:** {fmt_money(total)}")

                # Product link (optional)
                if it.get("link"):
                    # Most SerpAPI results provide a product page link; show it if present
                    st.markdown(f"[🔗 View Product]({it['link']})")
                else:
                    st.caption("No direct product link available.")

                # Maps search (optional utility)
                st.markdown(f"[📍 Search this store in {city} on Google Maps]({maps_url})")

        st.divider()
        st.subheader("🧠 AI Recommendation")
        st.write(ai_summary(city, tax, rows))

else:
    st.info("Enter a product and click **Search** to see Bay Area prices.")
