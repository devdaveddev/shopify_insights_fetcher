# app/utils.py
import re
import httpx
from typing import Tuple, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# regex patterns
email_re = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# fallback phone regex (simple)
phone_re = re.compile(r"\+?\d[\d\-\s]{6,}\d")

def normalize_base(url: str) -> str:
    """Ensure URL starts with http(s) and strip trailing slash."""
    u = url.strip()
    if not u.startswith("http"):
        u = "https://" + u
    return u.rstrip("/")

def soup_text_excerpt(html: str, length: int = 20000) -> str:
    """Extract plain text from HTML (truncate to given length)."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(" ", strip=True)[:length]

def extract_emails_and_phones_from_soup(soup: BeautifulSoup) -> Tuple[List[str], List[str]]:
    """Extract emails and phone numbers from soup text."""
    text = soup.get_text(" ")
    emails = list(set(email_re.findall(text)))
    phones = list(set(phone_re.findall(text)))
    # cleanup phones
    phones = [p.strip() for p in phones]
    return emails, phones

def join_url(base: str, href: str) -> Optional[str]:
    """Safely join relative links to base URL."""
    if not href:
        return None
    return href if href.startswith("http") else urljoin(base, href)

# ---------------- COMPETITOR LOGIC ---------------- #

def extract_competitor_links(html: str, base_url: str) -> List[str]:
    """
    Extract possible competitor links (heuristic):
    - Look for outbound <a href> links
    - Exclude social media / known CDN / same-domain links
    """
    soup = BeautifulSoup(html, "lxml")
    competitors = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = join_url(base_url, href)
        if not full_url:
            continue
        # Skip if it points to same site or social media
        if base_url in full_url:
            continue
        if any(social in full_url for social in ["facebook.com", "instagram.com", "twitter.com", "linkedin.com"]):
            continue
        # crude competitor heuristic: keep e-commerce looking links
        if any(kw in full_url for kw in ["shop", "store", "products", "collections"]):
            competitors.append(full_url)
    return list(set(competitors))

async def fetch_html(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch raw HTML from a URL with httpx (async)."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                return resp.text
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}")
    return None


import re
# import requests
from urllib.parse import urlparse

def find_competitors(brand_url: str):
    """
    Naive competitor finder: 
    1. Extracts brand name from domain.
    2. Uses a static mapping of known competitors (MVP approach).
    """

    domain = urlparse(brand_url).netloc
    brand = domain.split(".")[0]  # crude brand name extraction

    # Example competitor mapping (expand later with web search logic)
    competitors_map = {
        "allbirds": ["rothys.com", "nike.com", "adidas.com"],
        "gymshark": ["aloyoga.com", "lululemon.com", "underarmour.com"],
        "warbyparker": ["ray-ban.com", "eyebuydirect.com", "zennioptical.com"],
    }

    for key, rivals in competitors_map.items():
        if key in brand.lower():
            return rivals

    return []  # no known competitors# no known competitors
