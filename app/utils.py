# app/utils.py
import re
from typing import Tuple, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin

email_re = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# fallback phone regex (simple)
phone_re = re.compile(r"\+?\d[\d\-\s]{6,}\d")

def normalize_base(url: str) -> str:
    u = url.strip()
    if not u.startswith("http"):
        u = "https://" + u
    return u.rstrip("/")

def soup_text_excerpt(html: str, length: int = 20000) -> str:
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(" ", strip=True)[:length]

def extract_emails_and_phones_from_soup(soup: BeautifulSoup) -> Tuple[List[str], List[str]]:
    text = soup.get_text(" ")
    emails = list(set(email_re.findall(text)))
    phones = list(set(phone_re.findall(text)))
    # cleanup phones: strip spaces
    phones = [p.strip() for p in phones]
    return emails, phones

def join_url(base: str, href: str) -> str:
    if not href:
        return None
    return href if href.startswith("http") else urljoin(base, href)
