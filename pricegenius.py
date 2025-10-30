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

# --- Local SF store + farmers market data ---
LOCAL_STORES = {
    # Supermarkets
    "Safeway": "multiple SF locations — Mission, Marina, Castro, SOMA",
    "Trader Joe's": "7 SF stores — North Beach, SOMA, Lakeshore, Castro, Masonic, Stonestown, Nob Hill",
    "Whole Foods": "4 SF stores — SOMA, Potrero Hill, Haight, Ocean Ave",
    "Bi-Rite Market": "Mission District, Western Addition",
    "Mollie Stone’s": "Twin Peaks, Pacific Heights",
    "Good Life Grocery": "Bernal Heights, Potrero Hill",
    "Rainbow Grocery": "SOMA (Folsom St)",
    "Costco": "11th Street, SoMa",
    "Nob Hill Foods": "San Bruno (Peninsula)",
    # Specialty grocers
    "Luke’s Local": "Cole Valley, Cow Hollow, Laurel Heights, Noe Valley, Hayes Valley",
    "Epicurean Trader": "Cow Hollow, Mission, Laurel Village, Ferry Building, Bernal Heights",
    "Berkeley Bowl": "Berkeley (for comparison)",
    # Coffee & beverage
    "Philz Coffee": "Mission, Castro, Embarcadero, Dogpatch, Potrero Hill, SoMa",
    "Ritual Coffee Roasters": "Mission, Haight, Hayes Valley, Bayview",
    "Blue Bottle Coffee": "Hayes Valley, Ferry Building, SOMA, Mission Bay",
    "Boba Guys": "Mission, Hayes Valley, Potrero Hill, Downtown",
    # Ethnic markets
    "99 Ranch": "Daly City",
    "H Mart": "Daly City, San Jose",
    "New May Wah Market": "Inner Richmond (Clement St)",
    "Kwon's Market": "SOMA (7th Street)",
    # Farmers markets (with addresses)
    "Ferry Plaza Farmers Market": "1 Ferry Building, SF, CA 94105",
    "Heart of the City Farmers Market": "1182 Market St, SF, CA 94102",
    "Fort Mason Farmers Market": "2 Marina Blvd, SF, CA 94123",
    "Noe Valley Farmers Market": "3861 24th St, SF, CA 94114",
    "Alemany Farmers Market": "100 Alemany Blvd, SF, CA 94110"
}

# --- Helper functions ---
def money(x):
    try:
        return f"${float(x):.2f}"
    except Exception:
        return str(x)

def maps_link(store_name: str):
    """Return a Google Maps search link for the given store in SF."""
    location = LOCAL_STORES.get(store_name)
    if location:
        q = quote_plus(f"{store_name} {location}")
    else:
        q = quote_plus(f"{store_name} San Francisco")
    return f"https://www.google.com/maps/search/?api=1&query={q}"

def product_link(raw_link: str | None) -> str | None:
    """Return a clean, absolute URL."""
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
    """Make AI text one clean paragraph."""
    return " ".join(str(s).split())

# --- Streamlit UI ---
st.set_page_config(page_title="HellaCheap SF", page_icon="🛒", layout="centered")
st.title("🛒 HellaCheap SF")
st.markdown(
    "Compare **real-time San Francisco grocery prices** — powered by SerpAPI + OpenAI.\n\n"
    "_Pulls live listings from Google Shopping and summarizes the best deals from local stores._"
)

st.divider()
st.caption("💸 Tax rate applied: **9.625%**")

query = st.text_input("Search any product (e.g., oat milk, okra, Philz Coffee, PS5):")
st.divider()

# --- Search & results ---
if query:
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
        st.subheader(f"💰 San Francisco Prices (including tax @ {tax_rate}%)")

        for item in results[:15]:
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
                    st.image(img, width=220)

                location = LOCAL_STORES.get(store, "San Francisco area")
                st.caption(f"**{store}** — *{location}*")

                st.write(f"**Price:** {money(base_price)}")
                st.write(f"💵 **Total after tax:** {money(total)}")

                url = product_link(item.get("link") or item.get("product_link"))
                if url:
                    st.markdown(f'<a href="{url}" target="_blank">🔗 View Product</a>', unsafe_allow_html=True)
                else:
                    st.caption("No product link available")

                # Maps link
                st.markdown(
                    f'<a href="{maps_link(store)}" target="_blank">📍 Find on Maps</a>',
                    unsafe_allow_html=True,
                )

        # --- AI Recommendation ---
        cheapest = min(
            (r for r in results if isinstance(r.get("extracted_price"), (float, int))),
            key=lambda r: r["extracted_price"],
            default=None,
        )

        if cheapest:
            prompt = (
                f"Summarize the best deal for '{query}' in San Francisco. "
                f"Cheapest store: {cheapest.get('source')} selling at ${cheapest.get('extracted_price')}. "
                "Explain briefly why it’s worth buying there."
            )
            ai = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            ai_text = ai.choices[0].message.content.strip()
            st.success(f"🧠 AI Recommendation: {oneline(ai_text)}")
