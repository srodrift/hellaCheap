import os
import requests
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# Page setup
st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")

st.markdown("""
    <h1 style='text-align:center;font-size:42px;margin-bottom:0;'>🛫 PricePilot</h1>
    <p style='text-align:center;color:gray;margin-top:0;'>
        Compare live prices across BestBuy, Walmart, and Google Shopping — powered by AI.
    </p>
""", unsafe_allow_html=True)


# Fetch product data
def fetch_prices(product):
    if not SERPAPI_KEY:
        st.error("❌ Missing SERPAPI_KEY in environment.")
        return []

    url = "https://serpapi.com/search.json"
    params = {"engine": "google_shopping", "q": product, "api_key": SERPAPI_KEY, "hl": "en", "gl": "us", "num": 10}

    res = requests.get(url, params=params)
    data = res.json()
    results = []

    for r in data.get("shopping_results", [])[:5]:
        title = r.get("title", "Unknown Product")
        store = r.get("source", "Unknown Store")
        link = r.get("link", "")
        price = r.get("extracted_price") or r.get("price")
        image = r.get("thumbnail") or r.get("image")
        if link and link.startswith("http"):
            domain = link.split("/")[2].replace("www.", "")
        else:
            domain = "N/A"
        results.append({"title": title, "store": store, "price": price, "link": link, "domain": domain, "image": image})
    return results


# AI recommendation
def analyze_prices(prices):
    if not prices:
        return "No price data available."
    table = "\n".join([f"{p['store']}: ${p['price']}" for p in prices])
    prompt = f"Here are prices:\n{table}\n\nWhich store offers the best deal and why? Keep it under 3 sentences, friendly tone, end with an emoji."
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI unavailable ({str(e)})"


# Main app
product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

if product:
    with st.spinner("🔍 Searching for best deals..."):
        prices = fetch_prices(product)

    if prices:
        st.markdown("<h3 style='color:#f5b400;'>💰 Price Results</h3>", unsafe_allow_html=True)

        for p in prices:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:12px;
                            background-color:#fafafa;border-radius:10px;
                            padding:10px 15px;margin:10px 0;
                            border:1px solid #e5e7eb;">
                    <img src="{p.get('image','')}" width="60" style="border-radius:8px;" />
                    <div>
                        <b>{p['store']}</b> — <span style="color:#16a34a;font-weight:600;">${p['price']}</span><br>
                        <a href="{p['link']}" target="_blank" style="color:#2563eb;text-decoration:none;">🌐 {p['domain']}</a><br>
                        <span style="font-size:13px;color:#555;">{p['title']}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # AI Recommendation
        analysis = analyze_prices(prices)
        st.markdown("""
        <div style='background-color:#f0fdf4;border-left:6px solid #22c55e;
                    padding:15px;border-radius:10px;margin-top:20px;'>
            <h4 style='margin-bottom:10px;color:#047857;'>🧠 AI Recommendation</h4>
        """, unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:16px;'>{analysis}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning("No results found — try a more specific name.")

# Footer
st.markdown("""
---
<center>
<p style='color:gray;font-size:13px;'>
Built with ❤️ by Team PricePilot — powered by Streamlit, SerpAPI, and OpenAI
</p>
</center>
""", unsafe_allow_html=True)
