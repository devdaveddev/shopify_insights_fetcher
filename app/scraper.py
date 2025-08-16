# app/scraper.py
import asyncio
from typing import List, Optional, Dict, Tuple
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.models import Product
from app.utils import normalize_base, soup_text_excerpt, extract_emails_and_phones_from_soup, join_url
from app.config import USER_AGENT, TIMEOUT, PRODUCT_ENDPOINTS, MAX_HERO, MAX_FAQS
import re

HEADERS = {"User-Agent": USER_AGENT}

async def fetch_text(url: str, client: Optional[httpx.AsyncClient] = None) -> Tuple[int, str]:
    """Return (status_code, text) for given url."""
    close_client = False
    if client is None:
        client = httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT)
        close_client = True
    try:
        r = await client.get(url)
        return r.status_code, r.text
    finally:
        if close_client:
            await client.aclose()

async def allowed_by_robots(base: str, path: str = "/products.json") -> bool:
    robots_url = urljoin(base, "/robots.txt")
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=5.0) as client:
            r = await client.get(robots_url)
            if r.status_code != 200:
                return True
            txt = r.text.lower()
            # Simple conservative checks
            if f"disallow: {path.lower()}" in txt:
                return False
            if "disallow: /" in txt:
                return False
    except Exception:
        # Unable to fetch robots → proceed
        return True
    return True

def parse_products_from_json(resp_json: dict, base_url: str) -> List[Product]:
    products: List[Product] = []
    if not isinstance(resp_json, dict):
        return products
    for p in resp_json.get("products", []):
        images = [img.get("src") for img in p.get("images", []) if img.get("src")]
        prod = Product(
            id=p.get("id"),
            handle=p.get("handle"),
            title=p.get("title"),
            description=(p.get("body_html") or "").strip(),
            images=images,
            url=(f"{base_url}/products/{p.get('handle')}" if p.get("handle") else None)
        )
        variants = p.get("variants", [])
        if variants:
            try:
                prod.price = float(variants[0].get("price", 0))
            except Exception:
                prod.price = None
            try:
                cap = variants[0].get("compare_at_price")
                prod.compare_at_price = float(cap) if cap else None
            except Exception:
                prod.compare_at_price = None
        products.append(prod)
    return products

async def fetch_product_catalog(base: str) -> List[Product]:
    products: List[Product] = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT) as client:
        for path in PRODUCT_ENDPOINTS:
            url = base + path
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    try:
                        js = r.json()
                        products = parse_products_from_json(js, base)
                        if products:
                            # best-effort pagination (small number of pages)
                            for page in range(2, 6):
                                page_url = url + (f"&page={page}" if "?" in url else f"?page={page}")
                                rr = await client.get(page_url)
                                if rr.status_code != 200:
                                    break
                                try:
                                    jj = rr.json()
                                except Exception:
                                    break
                                more = parse_products_from_json(jj, base)
                                if not more:
                                    break
                                products.extend(more)
                            return products
                    except Exception:
                        continue
            except httpx.HTTPError:
                continue
    return products

def find_policy_links(soup: BeautifulSoup, base_url: str) -> Dict[str, Optional[str]]:
    links = {"privacy": None, "returns": None, "terms": None, "contact": None, "blog": None, "order_tracking": None, "about": None}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        hh = href.lower()
        if "privacy" in hh and not links["privacy"]:
            links["privacy"] = href if href.startswith("http") else urljoin(base_url, href)
        if ("return" in hh or "refund" in hh) and not links["returns"]:
            links["returns"] = href if href.startswith("http") else urljoin(base_url, href)
        if "terms" in hh and not links["terms"]:
            links["terms"] = href if href.startswith("http") else urljoin(base_url, href)
        if "contact" in hh and not links["contact"]:
            links["contact"] = href if href.startswith("http") else urljoin(base_url, href)
        if ("blog" in hh or "blogs" in hh) and not links["blog"]:
            links["blog"] = href if href.startswith("http") else urljoin(base_url, href)
        if ("order" in hh and "track" in hh) and not links["order_tracking"]:
            links["order_tracking"] = href if href.startswith("http") else urljoin(base_url, href)
        if ("about" in hh or "our-story" in hh or "/pages/about" in hh) and not links["about"]:
            links["about"] = href if href.startswith("http") else urljoin(base_url, href)
    return links

def extract_socials_and_contacts(soup: BeautifulSoup, base_url: str) -> Tuple[Dict[str,str], Dict[str,list]]:
    socials: Dict[str,str] = {}
    contacts: Dict[str,list] = {"emails": [], "phones": []}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "instagram.com" in href and "instagram" not in socials:
            socials["instagram"] = href
        if "facebook.com" in href and "facebook" not in socials:
            socials["facebook"] = href
        if "tiktok.com" in href and "tiktok" not in socials:
            socials["tiktok"] = href
        if ("twitter.com" in href or "x.com" in href) and "twitter" not in socials:
            socials["twitter"] = href
        if href.startswith("mailto:"):
            email = href.split("mailto:")[1].split("?")[0]
            contacts["emails"].append(email)
    emails, phones = extract_emails_and_phones_from_soup(soup)
    contacts["emails"] = list(set(contacts["emails"] + emails))
    contacts["phones"] = list(set(contacts["phones"] + phones))
    return socials, contacts

def extract_hero_products(soup: BeautifulSoup, base_url: str) -> List[str]:
    hero: List[str] = []
    candidates = []
    header = soup.select_one("header")
    main = soup.select_one("main") or soup.body
    if header:
        candidates.append(header)
    if main:
        candidates.append(main)
    for cls in ["hero", "featured", "carousel", "slider", "banner"]:
        candidates.extend(soup.select(f".{cls}"))
    for block in candidates:
        if not block:
            continue
        for a in block.find_all("a", href=True):
            if "/products/" in a["href"]:
                handle = a["href"].split("/products/")[-1].split("/")[0]
                hero.append(urljoin(base_url, f"/products/{handle}"))
    seen = set()
    out = []
    for r in hero:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out[:MAX_HERO]

async def fetch_page_text(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        code, text = await fetch_text(url)
        if code == 200:
            soup = BeautifulSoup(text, "lxml")
            return soup.get_text(" ", strip=True)[:20000]
    except Exception:
        return None
    return None

async def extract_faqs(soup: BeautifulSoup, base_url: str):
    faqs = []
    containers = soup.select(".faq, .faqs, [id*=faq], [class*=faq], .accordion, .toggle")
    for c in containers:
        for q in c.find_all(["h2","h3","h4","dt"]):
            nxt = q.find_next_sibling(["p","div","dd"])
            if nxt:
                faqs.append({"q": q.get_text(" ", strip=True), "a": nxt.get_text(" ", strip=True)})
    # fallback follow faq links
    if not faqs:
        for a in soup.find_all("a", href=True):
            if "faq" in a["href"].lower():
                href = a["href"]
                full = href if href.startswith("http") else urljoin(base_url, href)
                try:
                    code, txt = await fetch_text(full)
                    if code == 200:
                        s = BeautifulSoup(txt, "lxml")
                        for q in s.find_all(["h2","h3","h4"]):
                            nxt = q.find_next_sibling(["p","div"])
                            if nxt:
                                faqs.append({"q": q.get_text(" ", strip=True), "a": nxt.get_text(" ", strip=True)})
                except Exception:
                    continue
    return faqs[:MAX_FAQS]

async def scrape_shopify(base_url: str) -> Dict:
    # normalize
    base = normalize_base(base_url)
    # robots
    allowed = await allowed_by_robots(base)
    if not allowed:
        raise PermissionError("Scraping disallowed by robots.txt")
    # products
    product_catalog = await fetch_product_catalog(base)
    # homepage
    try:
        status, text = await fetch_text(base)
    except httpx.HTTPError as e:
        raise ConnectionError("Website unreachable") from e
    soup = BeautifulSoup(text, "lxml")
    socials, contacts = extract_socials_and_contacts(soup, base)
    policies = find_policy_links(soup, base)
    hero_urls = extract_hero_products(soup, base)
    # concurrent fetch of pages
    tasks = [
        fetch_page_text(policies.get("privacy")),
        fetch_page_text(policies.get("returns")),
        fetch_page_text(policies.get("about") or policies.get("contact")),
        extract_faqs(soup, base)
    ]
    privacy_text, returns_text, about_text, faqs = await asyncio.gather(*tasks)
    hero_products = []
    for u in hero_urls:
        hero_products.append(Product(url=u))
    result = {
        "url": base,
        "name": (soup.title.string.strip() if soup.title else None),
        "hero_products": hero_products,
        "product_catalog": product_catalog,
        "privacy_policy": privacy_text,
        "return_refund_policy": returns_text,
        "faqs": faqs,
        "social_handles": socials,
        "contact": contacts,
        "about": about_text,
        "important_links": policies
    }
    return result
