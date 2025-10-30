import os, requests, json
from openai import OpenAI

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
client = OpenAI(api_key=os.getenv("BLACKBOX_API_KEY"))

def fetch_prices(product):
    if not SERPAPI_KEY:
        raise ValueError("Missing SERPAPI_KEY")
    url = f"https://serpapi.com/search.json?q={product}&engine=google_shopping&api_key={SERPAPI_KEY}"
    r = requests.get(url)
    data = r.json()
    items = [
        {"store": i.get("source"), "price": i.get("extracted_price"), "url": i.get("link")}
        for i in data.get("shopping_results", [])[:5]
    ]
    return items

def analyze_options(prices):
    prompt = f"""
    You are a smart shopping assistant. Analyze the following JSON list of stores and prices,
    rank them by value, and explain which is the best option and why.

    {json.dumps(prices, indent=2)}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    product = input("Enter a product name: ") or "AirPods Pro 2"
    prices = fetch_prices(product)
    print("\n💰 Found Prices:\n", json.dumps(prices, indent=2))
    print("\n🧠 Analysis:\n", analyze_options(prices))
