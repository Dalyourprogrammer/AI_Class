import time
import requests
from urllib.parse import quote
from cache import get_cached_links, set_cached_links

BASE_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "WikipediaChainFinder/1.0 (Educational project; Python/requests)"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def _api_get(params, max_retries=3):
    """Make a GET request to the Wikimedia API with retry on failure."""
    for attempt in range(max_retries):
        resp = SESSION.get(BASE_URL, params=params)
        try:
            return resp.json()
        except requests.exceptions.JSONDecodeError:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise


def validate_article(title):
    """Validate that a Wikipedia article exists. Resolves redirects.
    Returns the canonical title, or None if the article does not exist."""
    params = {
        "action": "query",
        "titles": title,
        "redirects": 1,
        "format": "json",
    }
    resp = _api_get(params)
    pages = resp["query"]["pages"]
    page_id = next(iter(pages))
    if page_id == "-1" or "missing" in pages[page_id]:
        return None
    return pages[page_id]["title"]


def get_outgoing_links(title):
    """Get all outgoing article links (namespace 0) from a Wikipedia page."""
    cached = get_cached_links(title, "outgoing")
    if cached is not None:
        return cached

    links = []
    params = {
        "action": "query",
        "titles": title,
        "prop": "links",
        "plnamespace": 0,
        "pllimit": "max",
        "format": "json",
    }
    while True:
        resp = _api_get(params)
        pages = resp["query"]["pages"]
        page = next(iter(pages.values()))
        for link in page.get("links", []):
            links.append(link["title"])
        if "continue" in resp:
            params["plcontinue"] = resp["continue"]["plcontinue"]
        else:
            break

    set_cached_links(title, "outgoing", links)
    return links


def get_backlinks(title):
    """Get all pages that link to the given Wikipedia page (namespace 0)."""
    cached = get_cached_links(title, "backlinks")
    if cached is not None:
        return cached

    links = []
    params = {
        "action": "query",
        "list": "backlinks",
        "bltitle": title,
        "blnamespace": 0,
        "bllimit": "max",
        "format": "json",
    }
    while True:
        resp = _api_get(params)
        for bl in resp["query"]["backlinks"]:
            links.append(bl["title"])
        if "continue" in resp:
            params["blcontinue"] = resp["continue"]["blcontinue"]
        else:
            break

    set_cached_links(title, "backlinks", links)
    return links
