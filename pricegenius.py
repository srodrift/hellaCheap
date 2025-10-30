import os
import requests
import streamlit as st
from openai import OpenAI
from urllib.parse import urlparse

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
def clean_link(url, product):
    """Clean or replace bad Google redirect links."""
    if not url or "google.com" in url:
        # fallback to a readable search query
        return f"https://www.google.com/search?q={product.replace(' ', '+')}"
    return url

def fetch_prices(product):
    url = f"https://serpapi.com/search.json?q={product}&engine=google_shopping&api_key={SERPAPI_KEY}"
    response = requests.get(url)
    data = response.json()

    results = []
    for item in data.get("shopping_results", [])[:5]:
        store = item.get("source") or item.get("merchant") or "Unknown Store"
        price = item.get("extracted_price")
        link = item.get("link") or item.get("product_link") or item.get("product_page_url")

        link = clean_link(link, product)
        if price:
            # extract domain for nicer link label
            domain = urlparse(link).netloc.replace("www.", "")
            results.append({
                "store": store,
                "price": round(float(price), 2),
                "domain": domain,
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
        st.markdown("### 💰 Price Results")
        for p in prices:
            st.markdown(
                f"- **{p['store']}** — **${p['price']}** "
                f"[🌐 {p['domain']}]({p['link']})"
            )

        st.markdown("### 🧠 AI Recommendation")
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
