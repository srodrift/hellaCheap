import os
import requests
import streamlit as st
from urllib.parse import urlparse, quote_plus
from openai import OpenAI
from dotenv import load_dotenv

# -------------------- Setup --------------------
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

st.set_page_config(page_title="PricePilot", page_icon="🛫", layout="centered")
st.markdown("""
    <h1 style='text-align:center;font-size:42px;margin-bottom:0;'>🛫 PricePilot</h1>
    <p style='text-align:center;color:gray;margin-top:0;'>
        Compare live prices across BestBuy, Walmart, and Google Shopping — powered by AI.
    </p>
""", unsafe_allow_html=True)

# -------------------- Helpers --------------------
def safe_domain(link: str | None) -> str:
    """Return pretty domain (e.g., bestbuy.com) or 'N/A'."""
    if not link:
        return "N/A"
    try:
        netloc = urlparse(link).netloc
        return netloc.replace("www.", "") or "N/A"
    except Exception:
        return "N/A"

def best_link(item: dict, query: str) -> str | None:
    """
    Pick the best outbound link available from a SerpAPI Shopping item.
    We try 'link' → 'product_link' → 'product_page_url'.
    If nothing exists, we return a Google search link for the item title + store.
    """
    for key in ("link", "product_link", "product_page_url"):
        val = item.get(key)
        if isinstance(val, str) and val.startswith(("http://", "https://")):
            return val

    # Fallback: search link (only if we truly have nothing)
    title = item.get("title") or query
    store = item.get("source") or ""
    search_q = quote_plus(f"{title} {store}".strip())
    return f"https://www.google.com/search?q={search_q}"

def price_number(item: dict):
    """Return a numeric price if possible, otherwise None."""
    p = item.get("extracted_price")
    if p is None:
        # Try to parse 'price' which can be strings like '$129.99'
        raw = item.get("price")
        if isinstance(raw, (int, float)):
            p = float(raw)
        elif isinstance(raw, str):
            digits = "".join(ch for ch in raw if (ch.isdigit() or ch == ".")))
            p = float(digits) if digits else None
    return p

# -------------------- Fetch --------------------
def fetch_prices(product: str) -> list[dict]:
    if not SERPAPI_KEY:
        st.error("❌ Missing SERPAPI_KEY in environment.")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": product,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "gl": "us",
        "num": 10,
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    out: list[dict] = []
    for it in data.get("shopping_results", [])[:8]:
        price = price_number(it)
        if price is None:
            continue  # skip items without a usable price

        link = best_link(it, product)
        out.append({
            "title": it.get("title", "Unknown Product"),
            "store": it.get("source", "Unknown Store"),
            "price": round(float(price), 2),
            "link": link,
            "domain": safe_domain(link),
            "image": it.get("thumbnail") or it.get("image") or "",
        })
    return out

# -------------------- AI --------------------
def analyze_prices(prices: list[dict]) -> str:
    if not prices:
        return "No price data available."
    if not client:
        return "AI is not configured on this deployment."

    table = "\n".join([f"{p['store']}: ${p['price']}" for p in prices])
    prompt = (
        "Here are prices for the same product across stores:\n"
        f"{table}\n\n"
        "Which option is the best deal and why? Keep it under 3 sentences, friendly tone, end with an emoji."
    )
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI unavailable ({e})"

# -------------------- UI --------------------
product = st.text_input("Enter a product name (e.g. AirPods Pro 2):")

if product.strip():
    with st.spinner("🔍 Searching for best deals..."):
        items = fetch_prices(product.strip())

    if items:
        st.markdown("<h3 style='color:#f5b400;'>💰 Price Results</h3>", unsafe_allow_html=True)

        # Highlight the cheapest item (optional)
        cheapest = min(items, key=lambda x: x["price"])["price"]

        for p in items:
            is_best = p["price"] == cheapest
            border = "#22c55e" if is_best else "#e5e7eb"
            badge = (
                "<span style='background:#dcfce7;color:#166534;padding:2px 8px;"
                "font-size:12px;border-radius:999px;margin-left:8px;'>Best deal</span>"
                if is_best else ""
            )

            # Build link HTML only when we have a valid URL
            link_html = (
                f"<a href='{p['link']}' target='_blank' "
                f"style='color:#2563eb;text-decoration:none;'>🌐 {p['domain']}</a>"
                if p["link"] and p["link"].startswith(("http://", "https://"))
                else "<span style='color:#6b7280;'>No link</span>"
            )

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:14px;
                            background-color:#fafafa;border-radius:12px;
                            padding:14px 16px;margin:12px 0;
                            border:1px solid {border};">
                    <img src="{p['image']}" width="60" style="border-radius:8px;" />
                    <div>
                        <b>{p['store']}</b> — <span style="color:#16a34a;font-weight:700;">${p['price']}</span>
                        {badge}<br>
                        {link_html}<br>
                        <span style="font-size:13px;color:#555;">{p['title']}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # AI Recommendation
        st.markdown(
            "<div style='background-color:#f0fdf4;border-left:6px solid #22c55e;"
            "padding:15px;border-radius:10px;margin-top:20px;'>"
            "<h4 style='margin-bottom:10px;color:#047857;'>🧠 AI Recommendation</h4>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<p style='font-size:16px;'>{analyze_prices(items)}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No results found — try a more specific name.")

st.markdown("""
---
<center>
<p style='color:gray;font-size:13px;'>
Built with ❤️ by Team PricePilot — powered by Streamlit, SerpAPI, and OpenAI
</p>
</center>
""", unsafe_allow_html=True)
