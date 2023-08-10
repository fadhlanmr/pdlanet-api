from typing import Union
from fastapi import APIRouter, HTTPException
from ..function.webcrawl import web_crawl

router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def parse_html(url: str, class_list: Union[str, None] = None, action: str = 'encode'):
    crawl_result = web_crawl(url, class_list, action)
    return crawl_result.list_soup()