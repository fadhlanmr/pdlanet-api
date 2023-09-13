from fastapi import APIRouter, HTTPException
from ..function.api_call import call_api, list_thread, list_single_thread, if_catalog_list, if_board_list

router = APIRouter(
    prefix="/thread",
    tags=["thread"],
    responses={404: {"description": "Thread Endpoint not found, make sure a you're not a fed"}},
)

@router.get("/")
async def api_request(url: str, endpoint: str = None, board_code:str = None, thread: str = None):
    api_response = call_api(url=url, endpoint=endpoint, board_code=board_code, thread=thread)
    if endpoint == "boards":
        return if_board_list(api_response, False)
    if endpoint == "catalog":
        return if_catalog_list(api_response, False)
    return api_response

@router.get("/list-board")
async def api_board_list(url: str ='a.4cdn.org', endpoint: str = 'boards'):
    api_response = call_api(url, endpoint)
    return if_board_list(api_response, True)

@router.get("/list-catalog")
async def api_catalog_list(url: str ='a.4cdn.org', endpoint: str = 'catalog', board_code: str = None):
    api_response = list_thread(url, endpoint, board_code)
    return if_catalog_list(api_response, True)

@router.get("/single-thread")
async def api_single_thread(url: str, board_2_code: str, thread: str):
    api_response = list_single_thread(url, board_2_code, thread)
    return api_response
