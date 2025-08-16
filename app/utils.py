# app/utils.py
import re
import httpx
from typing import Tuple, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from app.config import GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID

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

async def find_competitors(brand_url: str):
    """
    Dynamically fetch competitor URLs using Google Custom Search API.
    """
    competitors = []

    # Extract brand name from the URL
    domain = urlparse(brand_url).netloc
    brand = domain.split(".")[0]  # crude brand name extraction

    # Use Google Custom Search API to find competitors
    search_query = f"competitors of {brand}"
    google_api_url = (
        f"https://www.googleapis.com/customsearch/v1"
        f"?key={GOOGLE_API_KEY}&cx={GOOGLE_SEARCH_ENGINE_ID}&q={search_query}"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(google_api_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract competitor URLs from search results
            for item in data.get("items", []):
                link = item.get("link")
                if link:
                    competitors.append(link)

    except Exception as e:
        print(f"[WARN] Failed to fetch competitors using Google API: {e}")

    return competitors
