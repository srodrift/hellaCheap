import os
import requests
import pandas as pd
import streamlit as st
from openai import OpenAI

# --------------------------
# 🌍 Load API keys
# --------------------------
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not SERPAPI_KEY:
    st.error("⚠️ Missing SERPAPI_KEY environment variable.")
if not OPENAI_KEY:
    st.error("⚠️ Missing OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=OPENAI_KEY)

# --------------------------
# 🔍 Fetch Prices from SerpAPI
# --------------------------
def fetch_prices(product):
    url = f"https://serpapi.com/search.json?q={product}&engine=google_shopping&api_key={SERPAPI_KEY}"
    response = requests.get(url)
    data = response.json()

    results = []
    for item in data.get("shopping_results", [])[:5]:
        store = item.get("source") or item.get("merchant") or "Unknown Store"
        price = item.get("extracted_price")

        # 🧼 Fix ugly Google redirect URLs
        link = (
            item.get("link")
            or item.get("product_link")
            or item.get("product_page_url")
        )
        if link and link.startswith("https://www.google.com/"):
            link = None
        if not link:
            link = f"https://www.google.com/search?q={product.replace(' ', '+')}"

        if price:
            results.append({
                "store": store,
                "price": round(float(price), 2),
                "link": link
            })
    return results


# --------------------------
# 🤖 Analyze Prices using GPT
# --------------------------
def analyze_prices(prices):
    if not prices:
        return "No prices found. Try another product."

    summary_prompt = (
        "You are a helpful shopping assistant. Here is a list of prices:\n\n"
        + "\n".join([f"{p['store']}: ${p['price']}" for p in prices])
        + "\n\nWhich is the best deal? "
          "Suggest whether the user should buy online or in-store. "
          "Keep the response short and friendly."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI analysis unavailable ({e})"


# --------------------------
# 💻 Streamlit UI
# --------------------------
st.set_page_config(page_title="PricePilot", page_icon="🛫")

st.title("🛫 PricePilot")
st.caption("Compare live prices across BestBuy, Walmart, and Google Shopping — powered by AI.")

product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

if product:
    with st.spinner("🔍 Fetching live prices..."):
        prices = fetch_prices(product)

    if prices:
        st.subheader("💰 Price Results")
        df = pd.DataFrame(prices)
        # clickable product links
        df["link"] = df["link"].apply(lambda x: f"[View Product]({x})")
        st.dataframe(df, use_container_width=True)

        st.subheader("🧠 AI Recommendation")
        with st.spinner("Analyzing best deal..."):
            analysis = analyze_prices(prices)
        st.success(analysis)
    else:
        st.warning("No results found for that product. Try again!")

# --------------------------
# 🧾 Footer
# --------------------------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: grey;'>
        Built with ❤️ by <b>SunnysideUp</b> · 
        <a href="https://github.com/srodrift/pricepilot" target="_blank">View on GitHub</a> · 
        Powered by <b>OpenAI</b> & <b>SerpAPI</b>
    </div>
    """,
    unsafe_allow_html=True
)
