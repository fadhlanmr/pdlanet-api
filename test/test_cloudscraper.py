import cloudscraper
from bs4 import BeautifulSoup
import urllib.parse
import re

SEARCH_URL = "https://republika.co.id/search/v3/?q="

def build_session() -> cloudscraper.CloudScraper:
    session = cloudscraper.create_scraper()
    session.headers.update({
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    })
    return session

def fetch_page(session: cloudscraper.CloudScraper, url: str) -> BeautifulSoup:
    resp = session.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}")
    return BeautifulSoup(resp.text, "html.parser")

def print_fetched_page(url: str, raw_limit: int = 1000) -> None:
    """Fetch `url`, print response info, raw HTML (truncated) and prettified soup.

    Args:
        url: The URL to fetch.
        raw_limit: Maximum number of raw HTML characters to print.
    """
    sess = build_session()
    try:
        soup = fetch_page(sess, url)
    except Exception as e:
        print(f"Error fetching page: {e}")
        return

    # Optionally print truncated raw HTML if the user needs it
    raw = str(soup)
    print("--- Raw HTML (truncated) ---")
    if len(raw) > raw_limit:
        _safe_print(raw[:raw_limit])
        _safe_print(f"... (truncated, total {len(raw)} chars)")
    else:
        _safe_print(raw)

    print("--- BeautifulSoup prettify ---")
    try:
        _safe_print(soup.prettify())
    except Exception as e:
        print(f"Error prettifying soup: {e}")


def print_search(query: str, raw_limit: int = 1000) -> None:
    """Build a search URL from `SEARCH_URL` and print the fetched page.

    Args:
        query: Search query string (will be appended to `SEARCH_URL`).
        raw_limit: Maximum number of raw HTML characters to print.
    """
    if not query:
        print("Empty query provided to print_search")
        return

    encoded = urllib.parse.quote_plus(query)
    url = SEARCH_URL + encoded

    sess = build_session()
    try:
        soup = fetch_page(sess, url)
    except Exception as e:
        print(f"Error fetching search page: {e}")
        return

    # Find text nodes that match the query (case-insensitive)
    matches = soup.find_all(string=re.compile(re.escape(query), re.I))

    seen = set()
    def _print_parent_of_string(m):
        parent = m.find_parent()
        # climb up to a reasonable container if available
        for tagname in ("article", "div", "section", "li", "a"):
            p = parent.find_parent(tagname) if parent else None
            if p is not None:
                parent = p
                break

        html_snippet = str(parent) if parent is not None else str(m)
        if html_snippet in seen:
            return False
        seen.add(html_snippet)
        print("--- Matching HTML component ---")
        _safe_print(parent.prettify() if hasattr(parent, 'prettify') else html_snippet)
        return True

    printed = 0
    if matches:
        for m in matches:
            if _print_parent_of_string(m):
                printed += 1
            if printed >= 5:
                break

    # Fallback: try finding a parent element containing all query tokens (order-insensitive)
    if printed == 0:
        print(f"Exact query '{query}' not found; trying token-based parent search...")
        tokens = re.findall(r"\w+", query)
        tokens = [t.lower() for t in tokens]
        # search candidate containers for tokens
        for tagname in ("article", "div", "section", "li", "a"):
            for parent in soup.find_all(tagname):
                text = parent.get_text(" ", strip=True).lower()
                if all(tok in text for tok in tokens):
                    html_snippet = str(parent)
                    if html_snippet in seen:
                        continue
                    seen.add(html_snippet)
                    print("--- Token-match HTML component ---")
                    try:
                        _safe_print(parent.prettify())
                    except Exception:
                        _safe_print(html_snippet)
                    printed += 1
                    if printed >= 5:
                        break
            if printed >= 5:
                break

    if printed == 0:
        print(f"No components found containing '{query}'. Dumping full page preview.")
        print_fetched_page(url, raw_limit=raw_limit)


def _safe_print(text: str) -> None:
    """Print text safely handling encoding errors on Windows consoles.

    Falls back to replacing unprintable characters.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))

def search_for_target(search_query: str, target: str, raw_limit: int = 150000) -> None:
    """Run a search for `search_query` and print HTML components that contain `target`.

    Args:
        search_query: query appended to SEARCH_URL (e.g., 'PLN').
        target: the text we expect to find within search results (e.g., 'Electricity Connect 2026').
        raw_limit: character limit for raw page dumps.
    """
    # perform the normal search page fetch
    encoded = urllib.parse.quote_plus(search_query)
    url = SEARCH_URL + encoded

    sess = build_session()
    try:
        soup = fetch_page(sess, url)
    except Exception as e:
        print(f"Error fetching search page for '{search_query}': {e}")
        return

    # look for the exact target text first
    matches = soup.find_all(string=re.compile(re.escape(target), re.I))
    if matches:
        print(f"Found exact target '{target}' in search results for '{search_query}'")
        seen = set()
        collected_links = []
        for m in matches:
            parent = m.find_parent()
            # prefer article/div sections
            for tagname in ("article", "div", "section", "li", "a"):
                p = parent.find_parent(tagname) if parent else None
                if p is not None:
                    parent = p
                    break
            html_snippet = str(parent) if parent is not None else str(m)
            if html_snippet in seen:
                continue
            seen.add(html_snippet)
            print("--- Matching HTML component (exact target) ---")
            _safe_print(parent.prettify() if hasattr(parent, 'prettify') else html_snippet)
            # try to extract an article link from this parent
            if parent is not None:
                a = parent.find('a', href=True)
                if a:
                    href = a['href'].strip()
                    title = a.get_text(strip=True)
                    collected_links.append({'title': title, 'url': href})

        # if we collected links, pick one to fetch
        if collected_links:
            chosen = collected_links[0]
            print(f"Fetching article from exact-match component: {chosen['url']}")
            art = fetch_article(chosen['url'])
            if art:
                out_path = 'output_article.json'
                save_json(art, out_path)
                print(f"Saved article to {out_path}")
        return
    # If no exact match, search for parent containers that contain both search_query and target tokens
    tokens = [t.lower() for t in re.findall(r"\w+", target)]
    found = False
    for tagname in ("article", "div", "section", "li", "a"):
        for parent in soup.find_all(tagname):
            text = parent.get_text(" ", strip=True).lower()
            if all(tok in text for tok in tokens):
                print("--- Matching HTML component (token match) ---")
                try:
                    _safe_print(parent.prettify())
                except Exception:
                    _safe_print(str(parent))
                found = True
                break
        if found:
            break

    if not found:
        print(f"Target '{target}' not found in search results for '{search_query}'. Full page dump:")
        print_fetched_page(url, raw_limit=raw_limit)
    else:
        # if we found components, try to extract article links and fetch first article
        # extract links from the search page and find the first that matches target tokens
        links = extract_article_links_from_search(soup)
        if links:
            # prefer the first link whose title contains target tokens
            tokens = [t.lower() for t in re.findall(r"\w+", target)]
            chosen = None
            for link in links:
                text = link['title'].lower()
                if all(tok in text for tok in tokens):
                    chosen = link
                    break
            if not chosen:
                chosen = links[0]
            print(f"Fetching article: {chosen['url']}")
            art = fetch_article(chosen['url'])
            if art:
                out_path = 'output_article.json'
                save_json(art, out_path)
                print(f"Saved article to {out_path}")


def extract_article_links_from_search(soup: BeautifulSoup) -> list:
    """Extract article links and titles from a Republika search result soup.

    Returns a list of dicts: {'title': ..., 'url': ...}
    """
    out = []
    # common pattern: div.news-title > a[href]
    for a in soup.select('div.news-title a'):
        href = a.get('href')
        title = a.get_text(strip=True)
        if href and title:
            out.append({'title': title, 'url': href.strip()})
    return out


def fetch_article(url: str) -> dict:
    """Fetch an article page and extract title, date, teaser and content."""
    sess = build_session()
    try:
        soup = fetch_page(sess, url)
    except Exception as e:
        print(f"Error fetching article {url}: {e}")
        return {}

    # heuristics based on test_crawl.py
    date_tag = soup.select_one("div.date.date-item__headline")
    date = date_tag.get_text(strip=True) if date_tag else ""
    title_tag = soup.select_one("div.max-card__title h1") or soup.select_one('h1')
    title = title_tag.get_text(strip=True) if title_tag else ""
    teaser_tag = soup.select_one("p.max-card__teaser")
    teaser = teaser_tag.get_text(strip=True) if teaser_tag else ""
    article_tag = soup.select_one('article')
    content = ""
    if article_tag:
        paragraphs = article_tag.find_all('p')
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])

    return {
        'url': url,
        'date': date,
        'title': title,
        'teaser': teaser,
        'content': content,
    }


def save_json(obj: dict, path: str) -> None:
    import json
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    search_for_target('PLN', 'Electricity Connect 2026')