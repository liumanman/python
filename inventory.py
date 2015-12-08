import os
import sys
from bs4 import BeautifulSoup
from bs4.element import Tag
import requests

_header = {
'Host': '',
'Connection': 'keep-alive',
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
'Upgrade-Insecure-Requests': '1',
'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
'Referer': '',
'Accept-Encoding': 'gzip, deflate, sdch',
'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6',
'Cookie': ''
}

_url_list = ['',
             '']


def get_inventory_list():
    html_content_list = _get_inventory_from_web()
    inventory_dict = {}
    for html in html_content_list:
        soup = BeautifulSoup(html, 'html.parser')
        tr_list = soup.select('.table-row')
        for tr in tr_list:
            td_list = [i for i in tr.contents if isinstance(i, Tag)]
            qty = int(td_list[6].select('font')[0].string)
            item_name = td_list[5].select('a')[0].string
            inventory_dict[item_name] = qty
    return inventory_dict


def _get_inventory_from_web():
    html_content_list = []
    for url in _url_list:
        res = requests.get(url, headers=_header)
        if res.status_code != 200:
            raise Exception('Fail to request inventory data.')
        html_content_list.append(res.text)
    return html_content_list


def get_item_list(file):
    abs_file_path = os.path.abspath(file)
    item_list = []
    with open(abs_file_path) as f:
        while 1:
            item_name = f.readline().strip().split('.')[0]
            if not item_name:
                break
            item_list.append(item_name)
    return item_list


def get_inventory(file):
    item_list = get_item_list(file)
    full_inventory_list = get_inventory_list()
    inventory_list = {item: full_inventory_list[item] for item in item_list}
    return inventory_list


def get_new_inventory(file):
    item_list = get_item_list(file)
    full_inventory_list = get_inventory_list()
    return {k: v for k, v in full_inventory_list.items() if k not in item_list and v > 5}


if __name__ == '__main__':
    for k, v in get_inventory(sys.argv[1]).items():
        print(k, v)
