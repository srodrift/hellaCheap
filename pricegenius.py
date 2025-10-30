import os
import streamlit as st
import requests
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------
# 🔐 Load environment variables
# -------------------------------
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# -------------------------------
# 🧭 Streamlit Config
# -------------------------------
st.set_page_config(page_title="🛒 HellaCheap SF", page_icon="💸", layout="centered")

st.title("🛒 HellaCheap SF")
st.write(
    """
Compare local prices across **Bay Area** stores — powered by **SerpAPI** and **OpenAI** 💡  
Some stores may repeat because of resellers, bundles, or stock differences.  
We show **only one lowest-priced listing per store**.
"""
)

# -------------------------------
# 💸 Bay Area Tax Rates
# -------------------------------
bay_area_taxes = {
    "San Francisco": 9.625,
    "Oakland": 10.25,
    "San Jose": 9.375,
    "Berkeley": 10.25,
    "Fremont": 9.25,
    "Palo Alto": 9.125,
    "Walnut Creek": 9.25,
}

city = st.selectbox("Select your Bay Area city:", list(bay_area_taxes.keys()))
tax_rate = bay_area_taxes[city]
st.markdown(f"💸 **Tax rate applied:** {tax_rate}%")

# -------------------------------
# 🔍 Search Input
# -------------------------------
query = st.text_input("Search any product (e.g., AirPods Pro, oat milk, PS5):")

# -------------------------------
# 🧾 Fetch Results
# -------------------------------
def fetch_results(search_query):
    """Fetch shopping results using SerpAPI"""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_shopping",
        "q": search_query,
        "location": "San Francisco Bay Area, California, United States",
        "api_key": SERPAPI_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "shopping_results" not in data:
        return []

    results = []
    for item in data["shopping_results"]:
        price_str = item.get("extracted_price")
        if not price_str:
            continue

        try:
            price = float(price_str)
        except (ValueError, TypeError):
            continue

        link = (
            item.get("link")
            or item.get("product_link")
            or item.get("shopping_url")
            or item.get("serpapi_link")
            or f"https://www.google.com/search?q={search_query}"
        )

        source = item.get("source") or item.get("merchant", {}).get("name")

        results.append(
            {
                "title": item.get("title"),
                "source": source,
                "price": price,
                "link": link,
            }
        )
    return results


# -------------------------------
# 🧠 AI Recommendation
# -------------------------------
def summarize_with_ai(product_name, cheapest_item, tax_rate):
    """Use OpenAI to create a concise friendly summary"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful shopping assistant that compares prices across local stores.",
                },
                {
                    "role": "user",
                    "content": f"The cheapest {product_name} is '{cheapest_item['title']}' from {cheapest_item['source']} priced at ${cheapest_item['price']:.2f}. The Bay Area tax rate is {tax_rate}%. Recommend why it's the best deal in a short, friendly tone.",
                },
            ],
        )
        summary = completion.choices[0].message.content.strip()
        clean_summary = (
            summary.replace("\n", " ").replace("\r", "").replace("  ", " ").strip()
        )
        return clean_summary
    except Exception as e:
        return f"(AI summary unavailable: {e})"


# -------------------------------
# 💰 Main Search + Display
# -------------------------------
if query:
    st.markdown(f"### 💰 {city} Prices (including tax)")
    st.markdown(f"Tax rate applied: **{tax_rate}%**")

    results = fetch_results(query)

    if not results:
        st.warning("No results found. Try a different search term!")
    else:
        # Keep lowest price per store
        df = pd.DataFrame(results)
        df = df.sort_values("price").drop_duplicates(subset="source", keep="first")

        for _, row in df.iterrows():
            total = round(row["price"] * (1 + tax_rate / 100), 2)
            store = row["source"] or "Unknown Store"

            st.markdown(f"**{row['title']}**")
            st.write(f"{store} — **${row['price']:.2f}**")
            st.write(f"Total after tax: **${total:.2f}**")

            # Google Maps link
            store_query = f"{store} {city}"
            maps_url = f"https://www.google.com/maps/search/{store_query.replace(' ', '+')}"
            st.markdown(f"[📍 Find on Maps]({maps_url})")

            # Product link
            if row["link"] and row["link"] != "#":
                st.markdown(f"[🔗 View Product]({row['link']})")
            else:
                st.caption("No product link available")

            st.markdown("---")

        # AI Summary
        cheapest = df.iloc[0].to_dict()
        ai_summary = summarize_with_ai(query, cheapest, tax_rate)
        st.markdown(f"### 🧠 AI Recommendation\n\n{ai_summary}")

else:
    st.info("👆 Enter a product above to start comparing prices!")
