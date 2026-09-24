import requests
from bs4 import BeautifulSoup
from datetime import datetime

SEARCH_URL = "https://republika.co.id/search/v3/?q="
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_republika_results(keyword):
    url = f"{SEARCH_URL}{keyword}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for item in soup.select("div.news-item"):
        title_tag = item.select_one("div.news-title a")
        date_tag = item.select_one("div.news-source")
        desc_tag = item.select_one("div.news-description")

        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag["href"].strip()
            date = date_tag.get_text(strip=True) if date_tag else ""
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            results.append({
                "title": title,
                "url": link,
                "time": date,
                "summary": desc
            })
    return results

def fetch_article_content(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract the date/time
    date_tag = soup.select_one("div.date.date-item__headline")
    date = date_tag.get_text(strip=True) if date_tag else ""

    # Extract the title
    title_tag = soup.select_one("div.max-card__title h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Extract teaser paragraph if available
    teaser_tag = soup.select_one("p.max-card__teaser")
    teaser = teaser_tag.get_text(strip=True) if teaser_tag else ""

    # Extract the main article text inside <article>
    article_tag = soup.select_one("article")
    content = ""
    if article_tag:
        paragraphs = article_tag.find_all("p")
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])

    return {
        "url": url,
        "date": date,
        "title": title,
        "teaser": teaser,
        "content": content
    }

def month_name_to_int(date_str):
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12
    }
    for name, num in months.items():
        if name in date_str.lower():
            return num
    return None

keyword = "pln"
articles = fetch_republika_results(keyword)
article_link=[]
for art in articles:
    print(f"{art['time']:25} | {art['title']}")
    print(f"{art['url']}")
    article_link.append((art['url'],art['time']))
    print(f"{art['summary']}")
    print("-"*3)
count = 0
for article_url, article_time in article_link:
    article_data = fetch_article_content(article_url)
    date_init = article_time.split(" ")
    date = int(date_init[0])
    month = month_name_to_int(date_init[1])
    year = int(date_init[2].split(",")[0])
    id_title = unique_id = "".join(word[0] for word in article_data['title'].split() if word).upper()
    id = f"{year}{month:02}{date:02}-{id_title}"
    print(f"\n\nArticle ID: {id}")
    print("Source: Republika")
    print(f"Crawled At: {datetime.now()}")
    print(f"Date: {date:02}-{month:02}-{year}")
    print(f"Title: {article_data['title']}")
    print(f"URL: {article_url}")
    print(f"Content:\n{article_data['content']}")
    count += 1
    if count >= 2:
        break