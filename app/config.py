# app/config.py
TIMEOUT = 10.0
USER_AGENT = "Mozilla/5.0 (compatible; InsightsFetcher/1.0; +https://example.com/bot)"
PRODUCT_ENDPOINTS = [
    "/products.json",
    "/collections/all/products.json",
    "/collections/all/products.json?limit=250"
]
# crawler limits
MAX_HERO = 10
MAX_FAQS = 30
