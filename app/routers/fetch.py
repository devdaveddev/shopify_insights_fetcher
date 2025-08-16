# app/routers/fetch.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import BrandContext
from scraper import scrape_shopify

router = APIRouter()

class FetchRequest(BaseModel):
    website_url: str

@router.post("/fetch", response_model=BrandContext)
async def fetch_store(req: FetchRequest):
    url = req.website_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="website_url required")
    try:
        data = await scrape_shopify(url)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal error: {str(e)}")
    try:
        bc = BrandContext(
            url=data.get("url"),
            name=data.get("name"),
            hero_products=data.get("hero_products", []),
            product_catalog=data.get("product_catalog", []),
            privacy_policy=data.get("privacy_policy"),
            return_refund_policy=data.get("return_refund_policy"),
            faqs=data.get("faqs", []),
            social_handles=data.get("social_handles", {}),
            contact=data.get("contact", {"emails": [], "phones": []}),
            about=data.get("about"),
            important_links=data.get("important_links", {})
        )
        return bc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"schema error: {str(e)}")
