from typing import List, Optional, Dict
from pydantic import BaseModel, HttpUrl

class Product(BaseModel):
    id: Optional[int] = None
    handle: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    images: List[HttpUrl] = []
    url: Optional[HttpUrl] = None

class BrandContext(BaseModel):
    url: HttpUrl
    name: Optional[str] = None
    hero_products: List[Product] = []
    product_catalog: List[Product] = []
    privacy_policy: Optional[str] = None
    return_refund_policy: Optional[str] = None
    faqs: List[Dict] = []   # [{"q":..., "a":...}]
    social_handles: Dict[str, Optional[str]] = {}
    contact: Dict[str, list] = {}  # {"emails": [...], "phones":[...]}
    about: Optional[str] = None
    important_links: Dict[str, Optional[str]] = {}

class CompetitorContext(BaseModel):
    main_brand: BrandContext
    competitors: List[BrandContext] = []
