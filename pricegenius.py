import os
import streamlit as st
import requests
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------------
# 🔐 Load environment variables
# -----------------------------------
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# -----------------------------------
# 🧭 Streamlit Config
# -----------------------------------
st.set_page_config(page_title="🛒 HellaCheap SF", page_icon="💸", layout="centered")
st.title("🛒 HellaCheap SF")
st.caption(
    "Compare local prices across Bay Area stores — powered by SerpAPI and OpenAI 💡\n\n"
    "Results come from public shopping listings. Some stores may repeat due to bundles or stock differences. "
    "We show only one **lowest-priced listing per store**."
)

# -----------------------------------
# 💸 Bay Area Tax Rates
# -----------------------------------
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

# -----------------------------------
# 🔍 Search Input
# -----------------------------------
query = st.text_input("Search any product (e.g., AirPods Pro, oat milk, PS5):")

# -----------------------------------
# 🛒 Fetch Results from SerpAPI
# -----------------------------------
def fetch_results(search_query):
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
        price = item.get("extracted_price")
        if not price:
            continue

        try:
            price = float(price)
        except ValueError:
            continue

        # Extract product link (prefer direct merchant URLs)
        link = (
            item.get("product_link")
            or item.get("link")
            or item.get("source")  # fallback if missing
        )

        source = (
            item.get("source")
            or item.get("merchant", {}).get("name")
            or "Unknown Store"
        )

        results.append(
            {
                "title": item.get("title"),
                "source": source,
                "price": price,
                "link": link,
            }
        )
    return results


# -----------------------------------
# 🧠 AI Summary Generator
# -----------------------------------
def summarize_with_ai(product_name, cheapest_item, tax_rate):
    """Generate clean summary with OpenAI"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a smart, concise, friendly price comparison assistant for Bay Area shoppers.",
                },
                {
                    "role": "user",
                    "content": f"The cheapest {product_name} is '{cheapest_item['title']}' from {cheapest_item['source']} priced at ${cheapest_item['price']:.2f}. Bay Area tax is {tax_rate}%. Summarize this recommendation cleanly in one short paragraph without line breaks.",
                },
            ],
        )
        return " ".join(completion.choices[0].message.content.strip().split())
    except Exception as e:
        return f"(AI summary unavailable: {e})"


# -----------------------------------
# 💰 Display Section
# -----------------------------------
if query:
    st.markdown(f"### 💰 {city} Prices (including tax)")
    st.caption(f"Tax rate applied: {tax_rate}%")

    results = fetch_results(query)
    if not results:
        st.warning("No results found. Try another search.")
    else:
        df = pd.DataFrame(results)
        df = df.sort_values("price").drop_duplicates(subset="source", keep="first")

        for _, row in df.iterrows():
            total = round(row["price"] * (1 + tax_rate / 100), 2)
            st.markdown(f"#### {row['title']}")
            st.write(f"**{row['source']}** — ${row['price']:.2f}")
            st.write(f"💵 Total after tax: **${total:.2f}**")

            # Accurate Google Maps link
            maps_url = f"https://www.google.com/maps/search/{row['source'].replace(' ', '+')}+store+near+{city.replace(' ', '+')}"
            st.markdown(f"[📍 Find on Maps]({maps_url})")

            if row["link"] and not row["link"].startswith("https://www.google.com/shopping"):
                st.markdown(f"[🔗 View Product]({row['link']})")
            else:
                st.caption("No product link available")

            st.divider()

        # 🧠 AI summary
        cheapest = df.iloc[0].to_dict()
        ai_summary = summarize_with_ai(query, cheapest, tax_rate)
        st.markdown(f"### 🧠 AI Recommendation\n\n{ai_summary}")

else:
    st.info("👆 Enter a product to start comparing prices locally in the Bay Area!")
