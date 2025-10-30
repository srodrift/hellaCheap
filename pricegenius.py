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
            link = None  # discard fake redirect link
        if not link:
            link = f"https://www.google.com/search?q={product.replace(' ', '+')}"

        if price:
            results.append({
                "store": store,
                "price": round(float(price), 2),
                "link": link
            })
    return results
