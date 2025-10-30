import os
import requests
import streamlit as st
from urllib.parse import quote_plus
from dotenv import load_dotenv
from openai import OpenAI

# --- Load environment variables ---
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- SF Store Map (local chains + neighborhoods) ---
LOCAL_STORES = {
    "Safeway": "multiple SF neighborhoods — Mission, Marina, Castro, SOMA",
    "Trader Joe's": "7 locations — North Beach, SOMA, Lakeshore, Castro, Masonic, Stonestown, Nob Hill",
    "Bi-Rite Market": "Mission District and Western Addition",
    "Whole Foods": "SOMA, Potrero Hill, Haight, Ocean Ave",
    "Luke’s Local": "Cole Valley, Cow Hollow, Laurel Heights, Noe Valley, Hayes Valley",
    "Epicurean Trader": "Cow Hollow, Mission, Laurel Village, Ferry Building, Bernal Heights",
    "Good Life Grocery": "Bernal Heights, Potrero Hill",
    "Rainbow Grocery": "SOMA (Folsom St)",
    "Mollie Stone’s": "Twin Peaks, Pacific Heights",
    "Berkeley Bowl": "Berkeley (East Bay, for comparison)",
    "99 Ranch": "Daly City",
    "H Mart": "Daly City, San Jose",
    "New May Wah Market": "Inner Richmond (Clement St)",
    "Philz Coffee": "Mission, Castro, Embarcadero, Dogpatch, Potrero Hill, SoMa",
    "Ritual Coffee Roasters": "Mission, Haight, Hayes Valley, Bayview",
    "Blue Bottle Coffee": "Hayes Valley, Ferry Building, SOMA, Mission Bay",
    "Boba Guys": "Mission, Hayes Valley, Potrero Hill, Downtown",
    "Costco": "11th Street, SoMa",
    "Nob Hill Foods": "San Bruno",
    "Farmer’s Market": "Ferry Plaza, Fort Mason, Heart of the City, Noe Valley, Alemany"
}

# --- Utilities ---

def money(x):
    try:
        return f"${float(x):.2f}"
    except Exception:
        return str(x)

def maps_link(store_name: str, city: str = "San Francisco"):
    q = quote_plus(f"{store_name} {city}")
    return f"https://www.google.com/maps/search/?api=1&query={q}"

def product_link(raw_link: str | None) -> str | None:
    """Clean up SerpAPI links to always be absolute, clickable, external URLs."""
    if not raw_link:
        return None
    if isinstance(raw_link, dict):
        raw_link = raw_link.get("link") or raw_link.get("url") or ""
    link = str(raw_link).strip()
    if link and not link.startswith(("http://", "https://")):
        link = "https://" + link
    if link.startswith("https://") or link.startswith("http://"):
        return link
    return None

def oneline(s: str) -> str:
    return " ".join(str(s).split())

# --- Streamlit UI ---
st.set_page_config(page_title="HellaCheap SF", page_icon="🛒", layout="centered")

st.title("🛒 HellaCheap SF")
st.markdown(
    "Compare **real-time Bay Area grocery prices** — powered by SerpAPI + OpenAI.\n\n"
    "_Shows public listings from Google Shopping across SF stores, with one lowest-priced listing per merchant._"
)

st.divider()

city = "San Francisco"
st.caption(f"💸 Tax rate applied: **9.625%**")

query = st.text_input("Search any product (e.g., oat milk, okra, Philz Coffee, PS5):")
st.divider()

if query:
    # --- SerpAPI query ---
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_KEY,
        "gl": "us",
        "hl": "en",
    }
    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()

    results = data.get("shopping_results", [])
    tax_rate = 9.625

    if not results:
        st.warning("No results found. Try another product or check your SerpAPI key.")
    else:
        st.subheader(f"💰 {city} Prices (including tax @ {tax_rate}%)")
        for item in results[:15]:  # limit for neatness
            title = item.get("title", "Unnamed product")
            store = item.get("source") or item.get("seller") or "Unknown store"
            price_raw = item.get("extracted_price") or item.get("price")
            img = item.get("thumbnail") or item.get("image")

            try:
                base_price = float(price_raw)
                total = base_price * (1 + tax_rate / 100)
            except Exception:
                base_price, total = price_raw, price_raw

            with st.container(border=True):
                st.markdown(f"### {title}")
                if img:
                    st.image(img, width=200)

                # Show store + location/neighborhood
                location = LOCAL_STORES.get(store, "San Francisco area")
                st.caption(f"**{store}** — *{location}*")

                st.write(f"**Price:** {money(base_price)}")
                st.write(f"💵 **Total after tax:** {money(total)}")

                # Product link
                url = product_link(item.get("link") or item.get("product_link"))
                if url:
                    st.markdown(f'<a href="{url}" target="_blank">🔗 View Product</a>', unsafe_allow_html=True)
                else:
                    st.caption("No product link available")

                # Maps link
                st.markdown(
                    f'<a href="{maps_link(store, city)}" target="_blank">📍 Find on Maps</a>',
                    unsafe_allow_html=True,
                )

        # --- AI summary (optional fancy touch) ---
        cheapest = min(
            (r for r in results if isinstance(r.get("extracted_price"), (float, int))),
            key=lambda r: r["extracted_price"],
            default=None,
        )

        if cheapest:
            prompt = (
                f"Summarize the best deal for '{query}' in San Francisco.\n"
                f"Cheapest store: {cheapest.get('source')} selling at ${cheapest.get('extracted_price')}."
                f" Suggest why it’s a good buy, briefly."
            )
            ai = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            ai_text = ai.choices[0].message.content.strip()
            st.success(f"🧠 AI Recommendation: {oneline(ai_text)}")
