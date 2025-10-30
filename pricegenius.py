import streamlit as st
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import quote

# --- Load API Keys ---
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# --- Initialize OpenAI ---
client = OpenAI(api_key=OPENAI_KEY)

# --- SF Tax Rate ---
TAX_RATE = 0.09625  # 9.625%

# --- San Francisco Store Directory ---
LOCAL_STORES = {
    # --- Major Chains ---
    "Trader Joe's - SOMA": "555 9th St, San Francisco, CA 94103 (SoMa)",
    "Trader Joe's - Masonic": "2675 Geary Blvd, San Francisco, CA 94118 (Laurel Heights)",
    "Trader Joe's - Stonestown": "265 Winston Dr, San Francisco, CA 94132 (Stonestown Galleria)",
    "Trader Joe's - Castro": "2280 Market St, San Francisco, CA 94114 (Duboce Triangle)",
    "Trader Joe's - North Beach": "401 Bay St, San Francisco, CA 94133 (North Beach)",
    "Trader Joe's - Fisherman’s Wharf": "10 Bay St, San Francisco, CA 94133 (Wharf District)",
    "Trader Joe's - California St": "3 Masonic Ave, San Francisco, CA 94118 (Presidio Heights)",
    "Safeway - Market": "2300 16th St, San Francisco, CA 94103 (Mission)",
    "Safeway - Marina": "15 Marina Blvd, San Francisco, CA 94123 (Marina District)",
    "Safeway - Noriega": "2350 Noriega St, San Francisco, CA 94122 (Outer Sunset)",
    "Whole Foods - Stanyan": "690 Stanyan St, San Francisco, CA 94117 (Haight)",
    "Whole Foods - 4th St": "399 4th St, San Francisco, CA 94107 (South Beach)",
    "Whole Foods - Ocean Ave": "1150 Ocean Ave, San Francisco, CA 94112 (Ingleside)",
    "Costco": "450 10th St, San Francisco, CA 94103 (SoMa)",

    # --- Local & Community Markets ---
    "Bi-Rite Market - Divisadero": "550 Divisadero St, San Francisco, CA 94117 (Alamo Square)",
    "Bi-Rite Market - 18th St": "3639 18th St, San Francisco, CA 94110 (Mission)",
    "Bi-Rite Market - NOPA": "1745 Grove St, San Francisco, CA 94117 (NOPA)",
    "Gus’s Community Market - Harrison": "2111 Harrison St, San Francisco, CA 94110 (Mission)",
    "The Good Life Grocery - Cortland": "448 Cortland Ave, San Francisco, CA 94110 (Bernal Heights)",
    "Haight Street Market": "1530 Haight St, San Francisco, CA 94117 (Haight-Ashbury)",
    "Falletti Foods": "308 Broderick St, San Francisco, CA 94117 (NOPA)",
    "Andronico's Community Markets": "1200 Irving St, San Francisco, CA 94122 (Inner Sunset)",

    # --- Specialty & Gourmet ---
    "The Epicurean Trader - Bernal": "401 Cortland Ave, San Francisco, CA 94110 (Bernal Heights)",
    "The Epicurean Trader - Cow Hollow": "1909 Union St, San Francisco, CA 94123 (Cow Hollow)",
    "The Epicurean Trader - Hayes Valley": "465 Hayes St, San Francisco, CA 94102 (Hayes Valley)",
    "Luke's Local - Cole Valley": "960 Cole St, San Francisco, CA 94117 (Cole Valley)",
    "Luke's Local - Union": "2190 Union St, San Francisco, CA 94123 (Marina)",
    "Luke's Local - Valencia": "900 Valencia St, San Francisco, CA 94110 (Mission)",
    "The Real Food Company": "2140 Polk St, San Francisco, CA 94109 (Russian Hill)",

    # --- Specialty Coffee & Drinks ---
    "Philz Coffee - Folsom": "300 Folsom St, San Francisco, CA 94105 (East Cut)",
    "Philz Coffee - 24th St": "3101 24th St, San Francisco, CA 94110 (Mission)",
    "Ritual Coffee - Valencia": "1026 Valencia St, San Francisco, CA 94110 (Mission)",
    "Blue Bottle Coffee - Ferry Building": "1 Ferry Building, San Francisco, CA 94111 (Embarcadero)",
    "Boba Guys - Hayes Valley": "429 Hayes St, San Francisco, CA 94102 (Hayes Valley)",

    # --- Ethnic Markets ---
    "New May Wah Market": "707 Clement St, San Francisco, CA 94118 (Inner Richmond)",
    "99 Ranch Market": "5151 Geary Blvd, San Francisco, CA 94118 (Outer Richmond)",
    "H Mart": "3995 Alemany Blvd, San Francisco, CA 94132 (Ingleside)",
    "La Loma Produce": "2847 Mission St, San Francisco, CA 94110 (Mission)",
    "Casa Lucas Market": "2934 24th St, San Francisco, CA 94110 (Mission)",
    "Nijiya Market": "1737 Post St, San Francisco, CA 94115 (Japantown)",
}

# --- Farmers Markets ---
FARMERS_MARKETS = {
    "Ferry Plaza Farmers Market (Seasonal)": "1 Ferry Building, San Francisco, CA 94111 (Embarcadero)",
    "Heart of the City Farmers Market (Seasonal)": "1182 Market St, San Francisco, CA 94102 (Civic Center)",
    "Mission Community Market (Seasonal)": "22nd St & Bartlett St, San Francisco, CA 94110 (Mission)",
    "Fort Mason Farmers Market (Seasonal)": "2 Marina Blvd, San Francisco, CA 94123 (Fort Mason)",
    "Noe Valley Farmers Market (Seasonal)": "3861 24th St, San Francisco, CA 94114 (Noe Valley)",
}

# --- Streamlit UI ---
st.set_page_config(page_title="HellaCheap SF", page_icon="💸", layout="wide")
st.title("🛒 HellaCheap SF")
st.caption("Compare local San Francisco prices — powered by SerpAPI + OpenAI")

st.divider()
st.markdown("""
Results come from public shopping listings via SerpAPI.  
We show one lowest-priced listing per store.
""")

show_farmers = st.toggle("🌾 Show Seasonal Farmers' Markets", value=False)
STORES = {**LOCAL_STORES, **FARMERS_MARKETS} if show_farmers else LOCAL_STORES

query = st.text_input("Search any product (e.g., Philz Coffee, oat milk, PS5):")

if query:
    st.subheader(f"💰 San Francisco Prices (including tax @ {TAX_RATE*100:.3f}%)")

    params = {
        "engine": "google_shopping",
        "q": f'"{query}"',
        "location": "San Francisco, California, United States",
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY,
    }

    res = requests.get("https://serpapi.com/search", params=params)

    if res.status_code != 200:
        st.error("Error fetching data from SerpAPI.")
    else:
        data = res.json()
        results = data.get("shopping_results", [])
        if not results:
            st.warning("No results found. Try another product.")
        else:
            items = []
            for r in results:
                title = r.get("title", "Unnamed Product")
                source = r.get("source", "Unknown Store")
                price = r.get("extracted_price", 0.0)
                link = r.get("link", "")
                thumbnail = r.get("thumbnail")

                if link.startswith("https://www.google.com/search?"):
                    link = f"https://www.google.com/search?q={quote(title + ' ' + source)}"

                total = price * (1 + TAX_RATE)
                items.append((title, source, price, total, link, thumbnail))

            for title, source, price, total, link, thumbnail in items:
                st.markdown(f"### {title}")
                if thumbnail:
                    st.image(thumbnail, width=150)

                address = STORES.get(source, f"{source} — various SF locations")
                st.markdown(f"**{address}**")
                st.markdown(f"**Price:** ${price:.2f}  💵 **Total after tax:** ${total:.2f}")
                st.markdown(f"[🔗 View Product]({link})")

                maps_link = f"https://www.google.com/maps/search/{quote(source + ' San Francisco CA')}"
                st.markdown(f"📍 [Find on Maps]({maps_link})")
                st.divider()

            # --- AI Vibe Summary ---
            cheapest = min(items, key=lambda x: x[3])
            c_title, c_store, c_price, c_total, _, _ = cheapest
            prompt = (
                f"You're a witty San Franciscan shopping buddy. "
                f"The cheapest product is '{c_title}' from {c_store}, "
                f"priced at ${c_price:.2f} before tax and ${c_total:.2f} after "
                f"the city's {TAX_RATE*100:.2f}% rate. "
                f"Add a local touch, use fitting emojis (☕, 🥬, 🎮, 💄, 💸), "
                f"and keep it friendly — one casual sentence."
            )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You're a fun, local SF deal expert with a friendly tone."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
            )

            st.markdown("### 🧠 AI Recommendation")
            st.markdown(response.choices[0].message.content.strip().replace("\n", " "))
else:
    st.info("🔍 Type a product name above to get started!")
