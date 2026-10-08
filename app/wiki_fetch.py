"""
wiki_fetch.py — Wikipedia search and page content fetching.

Uses the MediaWiki Action API directly (no third-party wikipedia wrapper needed).
This keeps the mechanics transparent and avoids hidden HTTP behaviour.
"""

from __future__ import annotations

import re
import requests
from dataclasses import dataclass, field

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "wiki-qa-assistant/1.0 (educational project)"})


@dataclass
class PageData:
    title: str
    summary: str                      # Lead section / extract
    full_text: str                    # Full plain-text content
    links: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


def search_page(query: str) -> str:
    """
    Search Wikipedia and return the best-matching page title.
    Raises ValueError if no results are found.
    """
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
        "format": "json",
    }
    resp = SESSION.get(MEDIAWIKI_API, params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("query", {}).get("search", [])
    if not results:
        raise ValueError(f"No Wikipedia page found for query: {query!r}")
    return results[0]["title"]


def _get_extract(title: str) -> str:
    """Fetch the plain-text lead-section extract for a page."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "format": "json",
    }
    resp = SESSION.get(MEDIAWIKI_API, params=params, timeout=10)
    resp.raise_for_status()
    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    if "missing" in page:
        raise ValueError(f"Wikipedia page not found: {title!r}")
    return page.get("extract", "")


def _get_full_text(title: str) -> str:
    """Fetch the full plain-text content of a page."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": True,
        "format": "json",
    }
    resp = SESSION.get(MEDIAWIKI_API, params=params, timeout=15)
    resp.raise_for_status()
    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    if "missing" in page:
        raise ValueError(f"Wikipedia page not found: {title!r}")
    return page.get("extract", "")


def _get_links(title: str, limit: int = 30) -> list[str]:
    """Fetch internal Wikipedia links from a page (first `limit` links)."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "links",
        "pllimit": limit,
        "plnamespace": 0,
        "format": "json",
    }
    resp = SESSION.get(MEDIAWIKI_API, params=params, timeout=10)
    resp.raise_for_status()
    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    links = page.get("links", [])
    return [lnk["title"] for lnk in links]


def _get_categories(title: str, limit: int = 15) -> list[str]:
    """Fetch categories for a page, stripping the 'Category:' prefix."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "categories",
        "cllimit": limit,
        "format": "json",
    }
    resp = SESSION.get(MEDIAWIKI_API, params=params, timeout=10)
    resp.raise_for_status()
    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    cats = page.get("categories", [])
    cleaned = []
    for cat in cats:
        name = cat["title"].replace("Category:", "").strip()
        # Skip maintenance categories
        if not re.search(r"(articles|pages|stub|Wikipedia|CS1|All )", name):
            cleaned.append(name)
    return cleaned


def get_page_content(title: str) -> PageData:
    """
    Fetch summary, full text, links, and categories for a Wikipedia page title.
    Raises ValueError if the page doesn't exist.
    """
    summary = _get_extract(title)
    full_text = _get_full_text(title)
    links = _get_links(title)
    categories = _get_categories(title)
    return PageData(
        title=title,
        summary=summary,
        full_text=full_text,
        links=links,
        categories=categories,
    )
