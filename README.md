# Shopify Insights Fetcher (MVP)

FastAPI-based MVP that extracts structured brand insights from public Shopify storefronts **without** using the official Shopify API.

## What it returns (mandatory)
- Full product catalog (from /products.json or /collections/all/products.json) — id, handle, title, description, price, images, url
- Hero products (homepage product links)
- Privacy & return/refund policy (page text if available)
- FAQs (best-effort extraction)
- Social handles (Instagram, Facebook, TikTok, Twitter/X)
- Contact details (emails, phones)
- About / brand text (from About or Contact)
- Important links (privacy, returns, contact, blog, order-tracking)

## Quick install
```bash
python -m venv venv
source venv/bin/activate      # windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
