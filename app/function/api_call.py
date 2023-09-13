import requests
import datetime
from bs4 import BeautifulSoup
import json
from unicodedata import normalize

def unix_to_gmt (unix_num: int) -> str:
    date_raw = datetime.datetime.fromtimestamp(unix_num)
    date_gmt = f'{date_raw.strftime("%a")}, {date_raw.strftime("%d")} {date_raw.strftime("%b")} {date_raw.strftime("%Y")} {date_raw.strftime("%X")} GMT'

    return date_gmt

def call_api (url: str, endpoint: str=None, unix=None, board_code: str=None, thread: str=None) :
    if board_code is not None :
        if thread is not None :
            url_call = f"http://{url}/{board_code}/thread/{thread}.json"
        else:
            url_call = f"http://{url}/{board_code}/{endpoint}"
    else:
        url_call = f"http://{url}/{endpoint}"
    try:
        if unix is not None :
            last_get = unix_to_gmt(unix)
            headers = {'If-Modified-Since':last_get}
            response = requests.get(url_call, headers=headers)
        else:
            response = requests.get(url_call)
        response.raise_for_status()
        # below refers to requests stored status codes https://github.com/psf/requests/blob/main/requests/status_codes.py
        if response.status_code == requests.codes.ok :
            api_output = response.json()
            # encoderJson = json.dumps(resp, ensure_ascii=False).encode('utf-8')
            # api_output = json.loads(encoderJson)
        else :
            api_output = response.status_code
        
        return api_output

    except requests.exceptions.RequestException as error:
        print(f"Request failed: {error}")

#call_api(url.default, endpoint.catalog, unix_to_gmt(lgb), board_code='vt')

def list_thread (url: str, endpoint: str, board_code: str, thread_last_get=None) :
    url_thread = f"http://{url}/{board_code}/{endpoint}"
    try:
        if thread_last_get is not None:
            headers = {'If-Modified-Since':thread_last_get}
            response = requests.get(url_thread, headers=headers)
        else:
            response = requests.get(url_thread)
        response.raise_for_status()
        if response.status_code == requests.codes.ok :
            api_output = response.json()
        else :
            api_output = response.status_code
        return api_output

    except requests.exceptions.RequestException as error:
        print(f"Request failed: {error}")

def list_single_thread (url: str, board_code: str, thread_id: str, thread_last_get=None) :
    url_thread = f"{url}/{board_code}/thread/{thread_id}"
    headers = {'If-Modified-Since':thread_last_get}
    response = requests.get(url_thread, headers)
    # clean some column
    # response_cleaned store the cleaned response
    return response

def clean_html(input_html: str) -> str:
    input_html = input_html.replace("<br>", " ")
    cleantext = BeautifulSoup(input_html, 'html.parser')
    finaltext = normalize('NFKC', cleantext.get_text().strip()).encode('ascii', 'replace')
    return finaltext

def if_board_list(list_board: list, clean_text: bool) -> list:
    temp_list = list_board['boards']
    temp_board = list()
    for lists in temp_list:
        temp_dict = dict()
        for key, value in lists.items():
            if key == 'board' :
                temp_dict[key]=value
            if key == 'title' :
                vals = value.encode('utf-8')
                temp_dict[key]=vals.decode()
                if clean_text :
                    temp_dict[key]=clean_html(value)
            if key == 'meta_description':
                vals = value.encode('utf-8')
                temp_dict[key]=vals.decode()
                if clean_text :
                    temp_dict[key]=clean_html(value)
        temp_board.append(temp_dict)
    return temp_board

def if_catalog_list(list_board: list, clean_text: bool) -> list:
    temp_catalog = list()
    for pages in list_board:
        for lists in pages['threads']:
            temp_dict = dict()
            for key, value in lists.items():
                if key == 'no' :
                    temp_dict[key]=value
                if key == 'sub' :
                    vals = value.encode('utf-8')
                    temp_dict[key]=vals.decode()
                    if clean_text :
                        temp_dict[key]=clean_html(value)
                if key == 'com' :
                    vals = value.encode('utf-8')
                    temp_dict[key]=vals.decode()
                    if clean_text :
                        temp_dict[key]=clean_html(value)
                if key == 'time':
                    temp_dict[key]=value
                if key == 'replies':
                    temp_dict[key]=value
            temp_catalog.append(temp_dict)
    return temp_catalog