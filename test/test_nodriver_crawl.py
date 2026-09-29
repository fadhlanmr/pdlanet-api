#!/usr/bin/env python3
"""
bisnis_crawler.py
------------------
Crawl https://search.bisnis.com/?q=<query> WITHOUT a browser/webdriver.

Strategy (no Selenium/Playwright, only HTTP clients):
  1. Warm up a `requests` session on the homepage (grabs cookies, looks
     like a normal visit) then hit the search URL with browser-like headers.
  2. If that comes back blocked/challenged (403, 503, "Just a moment",
     "Checking your browser", cf-mitigated header, etc.), automatically
     retry the same request with `cloudscraper`, which solves basic
     Cloudflare JS/IUAM challenges without a real browser.
  3. Parse the HTML for search-result cards. Because the exact markup of
     search.bisnis.com could not be inspected from this environment (see
     README note below / the --debug flag), parsing uses SEVERAL fallback
     strategies rather than one brittle CSS selector:
       a) embedded state JSON (__NEXT_DATA__ / __NUXT_DATA__ / ld+json),
          which many Indonesian news sites (Bisnis.com included) use for
          SSR/hydration and which is far more reliable than scraping DOM
          text if present.
       b) generic DOM heuristic: any <a> whose href matches an article-url
          pattern (https://<sub>.bisnis.com/read/...) and whose text is
          long enough to be a headline.
       c) a last-resort "just grab every link that contains the query
          term" pass, mainly useful for sanity-checking the page you got
          back (challenge page vs real results).
  4. Filters/highlights any result whose title contains a target phrase
     (default: "EPI Bidik", to find things like "PLN EPI Bidik ...").
  5. Saves raw HTML (--debug) and results (JSON/CSV) to disk.

IMPORTANT / HONESTY NOTE (please read):
  I was not able to load search.bisnis.com from this sandbox to inspect
  its real HTML/JSON structure -- a direct fetch attempt came back
  flagged as bot-blocked before I could see the markup, and this
  environment has no outbound network access to iterate against the
  live site myself. So the selectors below are written defensively
  (multiple fallback strategies + raw-HTML dump) rather than hard-coded
  against markup I've actually seen. Run this on your machine, and if
  the DOM-heuristic parser (`parse_dom_fallback`) comes back empty,
  open the saved debug HTML file, find the real result-card selector,
  and drop it into `parse_dom_fallback` (there's a clearly marked spot).

Install:
    pip install requests beautifulsoup4 cloudscraper lxml

Usage:
    python bisnis_crawler.py -q "PLN"
    python bisnis_crawler.py -q "PLN" --highlight "EPI Bidik" --debug --pages 2
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

try:
    import cloudscraper  # type: ignore
    HAVE_CLOUDSCRAPER = True
except ImportError:
    HAVE_CLOUDSCRAPER = False

log = logging.getLogger("bisnis_crawler")

BASE = "https://search.bisnis.com/"
HOMEPAGE = "https://www.bisnis.com/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-site",
    "Referer": HOMEPAGE,
}

# Markers that usually mean "we got a challenge page, not real content"
CHALLENGE_MARKERS = [
    "just a moment",
    "checking your browser",
    "attention required",
    "cf-browser-verification",
    "cf-chl",
    "enable javascript and cookies",
    "ddos protection by",
    "__cf_chl_",
]

ARTICLE_URL_RE = re.compile(r"https?://[a-z0-9-]+\.bisnis\.com/read/", re.I)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    extracted_via: str = ""


def looks_like_challenge(html: str, status: int) -> bool:
    if status in (403, 429, 503):
        return True
    low = html.lower()
    return any(marker in low for marker in CHALLENGE_MARKERS)


def build_search_url(query: str, page: int = 1) -> str:
    params = {"q": query}
    if page > 1:
        params["page"] = page  # ASSUMPTION: adjust if the real site uses a
        # different param (e.g. "p", "pg") -- check the debug HTML / the
        # pagination links it contains and fix here if needed.
    return f"{BASE}?{urlencode(params)}"


def fetch_with_requests(url: str, session: requests.Session, timeout=20):
    resp = session.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    return resp.status_code, resp.text, dict(resp.headers)


def fetch_with_cloudscraper(url: str, timeout=25):
    if not HAVE_CLOUDSCRAPER:
        raise RuntimeError(
            "cloudscraper not installed. Run: pip install cloudscraper"
        )
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    resp = scraper.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    return resp.status_code, resp.text, dict(resp.headers)


def get_page(query: str, page: int, debug_dir: Optional[Path]) -> tuple[str, str]:
    """
    Returns (html, method_used). Tries plain requests first (with a
    homepage warm-up for cookies), falls back to cloudscraper if the
    response looks like a bot-challenge.
    """
    url = build_search_url(query, page)
    session = requests.Session()

    # Step 1: warm up on the homepage so we carry normal-looking cookies
    # into the search request (helps with simple bot checks; harmless if
    # unnecessary).
    try:
        session.get(HOMEPAGE, headers=DEFAULT_HEADERS, timeout=15)
    except requests.RequestException as e:
        log.warning("Homepage warm-up failed (continuing anyway): %s", e)

    method = "requests"
    try:
        status, html, headers = fetch_with_requests(url, session)
    except requests.RequestException as e:
        log.warning("requests fetch failed (%s); trying cloudscraper", e)
        status, html = 0, ""

    if status != 200 or looks_like_challenge(html, status):
        log.info(
            "Plain requests looked blocked/challenged (status=%s). "
            "Falling back to cloudscraper...",
            status,
        )
        method = "cloudscraper"
        try:
            status, html, headers = fetch_with_cloudscraper(url)
        except Exception as e:
            log.error("cloudscraper fetch also failed: %s", e)
            raise

    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        out = debug_dir / f"debug_page{page}_{method}.html"
        out.write_text(html, encoding="utf-8", errors="ignore")
        log.info("Saved raw HTML -> %s", out)

    if looks_like_challenge(html, status):
        log.error(
            "Still looks like a challenge/block page after cloudscraper "
            "(status=%s). See the saved debug HTML. This site may need a "
            "full JS-executing client (Cloudflare Turnstile etc.) which "
            "falls outside the requests/cloudscraper approach.",
            status,
        )

    return html, method


# ---------------------------------------------------------------------
# Parsing strategies
# ---------------------------------------------------------------------

def parse_embedded_json(html: str) -> list[SearchResult]:
    """Look for __NEXT_DATA__ / __NUXT_DATA__ / ld+json blocks and try to
    pull out anything that looks like an article list. This is a best-
    effort generic walker since the real schema is unknown from here."""
    results: list[SearchResult] = []
    soup = BeautifulSoup(html, "lxml")

    candidates = soup.find_all(
        "script", attrs={"id": re.compile(r"__NEXT_DATA__|__NUXT_DATA__")}
    )
    candidates += soup.find_all("script", attrs={"type": "application/ld+json"})

    def walk(node, depth=0):
        if depth > 12:
            return
        if isinstance(node, dict):
            title = node.get("title") or node.get("headline") or node.get("name")
            url = node.get("url") or node.get("link")
            if isinstance(title, str) and isinstance(url, str) and ARTICLE_URL_RE.match(url):
                results.append(
                    SearchResult(
                        title=title.strip(),
                        url=url.strip(),
                        snippet=(node.get("description") or "")[:300],
                        source="bisnis.com",
                        extracted_via="embedded_json",
                    )
                )
            for v in node.values():
                walk(v, depth + 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, depth + 1)

    for script in candidates:
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        walk(data)

    return dedupe(results)


def parse_dom_fallback(html: str) -> list[SearchResult]:
    """Generic DOM heuristic. If you've inspected the real search-result
    markup (via the --debug dump), REPLACE/extend the selector below with
    the actual result-card container for much cleaner titles/snippets."""
    soup = BeautifulSoup(html, "lxml")
    results: list[SearchResult] = []

    # <<< If you know the real container, prefer this exact-selector path >>>
    # e.g. for card in soup.select("div.search-result-item"): ...
    # for now: fall through to the generic link-based heuristic below.

    seen_urls = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE, a["href"])
        if not ARTICLE_URL_RE.match(href):
            continue
        text = " ".join(a.get_text(" ", strip=True).split())
        if len(text) < 15:  # skip nav/breadcrumb links, keep real headlines
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        results.append(
            SearchResult(title=text, url=href, source="bisnis.com", extracted_via="dom_link")
        )

    return results


def dedupe(results: list[SearchResult]) -> list[SearchResult]:
    seen = set()
    out = []
    for r in results:
        if r.url in seen:
            continue
        seen.add(r.url)
        out.append(r)
    return out


def parse_results(html: str) -> list[SearchResult]:
    results = parse_embedded_json(html)
    if not results:
        results = parse_dom_fallback(html)
    return dedupe(results)


# ---------------------------------------------------------------------
# Main crawl
# ---------------------------------------------------------------------

def crawl(query: str, pages: int, debug_dir: Optional[Path], delay: float) -> list[SearchResult]:
    all_results: list[SearchResult] = []
    for page in range(1, pages + 1):
        log.info("Fetching page %d for query=%r ...", page, query)
        html, method = get_page(query, page, debug_dir)
        page_results = parse_results(html)
        log.info("Page %d (%s): parsed %d result(s)", page, method, len(page_results))
        if not page_results:
            log.warning(
                "No results parsed on page %d. Either the query has no "
                "more results, the page was a challenge page, or the "
                "parser's selectors need adjusting (see --debug HTML).",
                page,
            )
        all_results.extend(page_results)
        if page < pages:
            time.sleep(delay)
    return dedupe(all_results)


def save_results(results: list[SearchResult], out_path: Path):
    if out_path.suffix.lower() == ".csv":
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url", "snippet", "source", "extracted_via"])
            writer.writeheader()
            for r in results:
                writer.writerow(asdict(r))
    else:
        out_path.write_text(
            json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    log.info("Saved %d result(s) -> %s", len(results), out_path)


def main():
    ap = argparse.ArgumentParser(description="Crawl search.bisnis.com without a webdriver.")
    ap.add_argument("-q", "--query", default="PLN", help="Search query (default: PLN)")
    ap.add_argument("--pages", type=int, default=1, help="How many result pages to fetch")
    ap.add_argument("--delay", type=float, default=1.5, help="Delay between page requests (s)")
    ap.add_argument(
        "--highlight",
        default="EPI Bidik",
        help='Substring to flag in the output, e.g. "EPI Bidik" to spot "PLN EPI Bidik ..."',
    )
    ap.add_argument("--out", default="bisnis_results.json", help="Output file (.json or .csv)")
    ap.add_argument("--debug", action="store_true", help="Save raw HTML of each fetched page")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if not HAVE_CLOUDSCRAPER:
        log.warning(
            "cloudscraper is not installed -- if the site is behind "
            "Cloudflare, plain `requests` alone will likely fail. "
            "Run: pip install cloudscraper"
        )

    debug_dir = Path("debug_html") if args.debug else None

    results = crawl(args.query, args.pages, debug_dir, args.delay)

    print(f"\n=== {len(results)} result(s) for query {args.query!r} ===\n")
    for r in results:
        flag = " <<< MATCH >>>" if args.highlight.lower() in r.title.lower() else ""
        print(f"- [{r.extracted_via}] {r.title}{flag}\n  {r.url}")

    matches = [r for r in results if args.highlight.lower() in r.title.lower()]
    print(f"\n{len(matches)} result(s) contain {args.highlight!r}.")

    save_results(results, Path(args.out))

    if not results:
        print(
            "\nNo results were parsed at all. Check the saved debug_html/*.html "
            "file(s) to see what was actually returned (real results page, "
            "empty state, or a bot-challenge page), then adjust "
            "parse_dom_fallback()/parse_embedded_json() accordingly.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()