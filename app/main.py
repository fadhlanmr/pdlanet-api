from typing import Union
from fastapi import FastAPI
import api.webcrawl as crawler 

app = FastAPI()


@app.get("/")
def read_root():
    return {"Pdlanet-API": "access api.pdlanet.com/docs for swagger"}

@app.get("/parser")
async def parse_html(url: str, class_list: str | None = None, action: str | None = 'encode'):
    crawl_result = crawler.web_crawl(url, class_list, action)
    return crawl_result.list_soup()

@app.get("/ryan/{gosling_id}")
def read_ryan_gosling(gosling_id: int, q: Union[str, None] = None):
    return {"You're Gosling #": gosling_id, "Why don't you say the baseline": q}
