import importlib.util
from pathlib import Path

from bs4 import BeautifulSoup

module_path = Path(__file__).resolve().parent / 'test_scraper_bisnis.py'
spec = importlib.util.spec_from_file_location('test_scraper_bisnis', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

extract_article_links_from_search = module.extract_article_links_from_search

HTML = '''
<html><body>
  <a href="https://search.bisnis.com/link?url=https%3A%2F%2Fekonomi.bisnis.com%2Fread%2F20260925%2F44%2F2007159%2Fpln-epi-bidik-potensi-606-juta-ton-biomassa">
    PLN EPI Bidik Potensi 60,6 Juta Ton Biomassa
  </a>
  <a href="https://search.bisnis.com/link?url=https%3A%2F%2Fekonomi.bisnis.com%2Fread%2F20260924%2F44%2F2006861%2Fpln-gandeng-mitra-dalam-5-kolaborasi-strategis-senilai-rp33-triliun">
    PLN Gandeng Mitra dalam 5 Kolaborasi Strategis Senilai Rp3,3 Triliun
  </a>
</body></html>
'''


def test_extract_article_links_from_search_handles_bisnis_search_links():
    soup = BeautifulSoup(HTML, 'html.parser')

    links = extract_article_links_from_search(soup)

    assert links[0]['title'] == 'PLN EPI Bidik Potensi 60,6 Juta Ton Biomassa'
    assert links[0]['url'] == 'https://ekonomi.bisnis.com/read/20260925/44/2007159/pln-epi-bidik-potensi-606-juta-ton-biomassa'
    assert links[1]['url'] == 'https://ekonomi.bisnis.com/read/20260924/44/2006861/pln-gandeng-mitra-dalam-5-kolaborasi-strategis-senilai-rp33-triliun'
