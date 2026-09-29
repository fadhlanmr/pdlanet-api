import argparse
import re
import urllib.parse
from typing import List, Dict, Any

import cloudscraper
from bs4 import BeautifulSoup

# Change this to the search engine you want to scrape.
# Working example: https://www.viva.co.id/search?q=
# Example target for this engine: "Electricity Connect 2026"
SEARCH_URL = "https://republika.co.id/search/v3/?q="


def build_session() -> cloudscraper.CloudScraper:
    session = cloudscraper.create_scraper()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    return session


def build_search_url(search_query: str) -> str:
    return f"{SEARCH_URL}{urllib.parse.quote_plus(search_query)}"


def normalize_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    raw_url = raw_url.strip()
    if raw_url.startswith("//"):
        raw_url = "https:" + raw_url
    if raw_url.startswith("/"):
        parsed = urllib.parse.urlparse(SEARCH_URL)
        base = f"{parsed.scheme}://{parsed.netloc}"
        raw_url = f"{base}{raw_url}"
    return raw_url


def fetch_search_page(search_query: str) -> tuple[str, BeautifulSoup]:
    search_url = build_search_url(search_query)
    session = build_session()
    response = session.get(search_url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return search_url, soup


def looks_like_search_result_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False

    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if host in {"sso.vdn.co.id", "www.viva.co.id"}:
        return path not in {"/", "/search", "/breakingnews", "/siap"}
    if host.endswith("viva.co.id"):
        return path not in {"/", "/search", "/breakingnews", "/siap"}
    return False


def extract_search_results(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract search result entries, not header or site navigation links."""
    results: List[Dict[str, Any]] = []
    seen = set()

    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        title = link.get_text(" ", strip=True)
        if not href or not title:
            continue

        url = normalize_url(href)
        if not looks_like_search_result_url(url):
            continue

        if len(title) < 20:
            continue

        parent = link.find_parent(["article", "li", "div", "section"])
        html_block = str(parent) if parent is not None else str(link)
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "title": title,
            "url": url,
            "text": title,
            "html": html_block,
        })

    return results[:20]


def target_matches(result: Dict[str, Any], target: str) -> bool:
    if not target:
        return True

    haystack = f"{result.get('title', '')} {result.get('text', '')}".lower()
    target_tokens = [token for token in re.findall(r"[a-z0-9]+", target.lower()) if len(token) > 2]
    if not target_tokens:
        return target.lower() in haystack
    return all(token in haystack for token in target_tokens)


def search_for_target(search_query: str, target: str, limit: int = 10) -> Dict[str, Any]:
    """Return matching results and their container HTML without fetching article pages."""
    search_url = build_search_url(search_query)

    try:
        fetched_url, soup = fetch_search_page(search_query)
        search_url = fetched_url
        results = extract_search_results(soup)
    except Exception as exc:
        return {
            "query": search_query,
            "target": target,
            "search_url": search_url,
            "error": str(exc),
            "results": [],
        }

    matches = [result for result in results if target_matches(result, target)] if target else results[:limit]
    if not target:
        matches = results[:limit]

    return {
        "query": search_query,
        "target": target,
        "search_url": search_url,
        "results": matches[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch search results and return matching result URLs and HTML blocks.")
    parser.add_argument("query", nargs="?", default="PLN", help="Search query, e.g. PLN")
    parser.add_argument("target", nargs="?", default="Electricity Connect 2026", help="Target text to match, e.g. Electricity Connect 2026")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results to return")
    args = parser.parse_args()

    payload = search_for_target(args.query, args.target, limit=args.limit)
    print(f"Search URL: {payload['search_url']}")
    print(f"Query: {payload['query']}")
    print(f"Target: {payload['target']}")
    if payload.get("error"):
        print(f"Error: {payload['error']}")
    print(f"Found results: {len(payload['results'])}")

    for index, result in enumerate(payload["results"], start=1):
        print(f"\n--- Result #{index} ---")
        print(result["title"])
        print(result["url"])
        print(result["html"][:1200])


if __name__ == "__main__":
    main()
