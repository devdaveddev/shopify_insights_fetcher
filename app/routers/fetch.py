# app/routers/fetch.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models import BrandContext, CompetitorContext
from app.scraper import scrape_shopify
from app.utils import find_competitors

router = APIRouter()

class FetchRequest(BaseModel):
    website_url: str

@router.post("/fetch", response_model=CompetitorContext)
async def fetch_store(req: FetchRequest):
    url = req.website_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="website_url required")
    try:
        # Fetch main brand insights
        main_data = await scrape_shopify(url)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal error: {str(e)}")

    try:
        main_brand = BrandContext(
            url=main_data.get("url"),
            name=main_data.get("name"),
            hero_products=main_data.get("hero_products", []),
            product_catalog=main_data.get("product_catalog", []),
            privacy_policy=main_data.get("privacy_policy"),
            return_refund_policy=main_data.get("return_refund_policy"),
            faqs=main_data.get("faqs", []),
            social_handles=main_data.get("social_handles", {}),
            contact=main_data.get("contact", {"emails": [], "phones": []}),
            about=main_data.get("about"),
            important_links=main_data.get("important_links", {})
        )

        # Find competitors
        competitor_urls = find_competitors(url)
        competitors = []

        for competitor_url in competitor_urls:
            try:
                competitor_data = await scrape_shopify(competitor_url)
                competitor_brand = BrandContext(
                    url=competitor_data.get("url"),
                    name=competitor_data.get("name"),
                    hero_products=competitor_data.get("hero_products", []),
                    product_catalog=competitor_data.get("product_catalog", []),
                    privacy_policy=competitor_data.get("privacy_policy"),
                    return_refund_policy=competitor_data.get("return_refund_policy"),
                    faqs=competitor_data.get("faqs", []),
                    social_handles=competitor_data.get("social_handles", {}),
                    contact=competitor_data.get("contact", {"emails": [], "phones": []}),
                    about=competitor_data.get("about"),
                    important_links=competitor_data.get("important_links", {})
                )
                competitors.append(competitor_brand)
            except Exception as e:
                print(f"[WARN] Failed to fetch competitor {competitor_url}: {e}")

        return CompetitorContext(main_brand=main_brand, competitors=competitors)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"schema error: {str(e)}")
