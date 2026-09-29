import requests
from bs4 import BeautifulSoup
import cloudscraper

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

SEARCH_URL = "https://www.inews.id/find?q="
KEYWORD = "PLN"
url = f"{SEARCH_URL}{KEYWORD}"
# response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
# response.raise_for_status()

# soup = BeautifulSoup(response.text, "html.parser")

session = build_session()
soup = fetch_page(session, url)

results = []
for item in soup.select('div.cardBody'):
    link_tag = item.select_one("a")
    title_tag = item.select_one("h3.cardTitle")

    if title_tag and link_tag:
        title = title_tag.get_text(strip=True)
        link = link_tag["href"].strip()
        results.append({
            "title": title,
            "url": link
        })

print("Search Results:")
for result in results:
    print(f"- {result['title']}: {result['url']}")