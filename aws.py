import requests
import time
from bs4 import BeautifulSoup

_sales_div_css_name = 'a-row a-spacing-mini olpOffer'
_price_div_css_name = 'a-size-large a-color-price olpOfferPrice a-text-bold'
_shippingfee_tag_css_name = 'olpShippingPrice'
_seller_tag_css_name = 'a-spacing-none olpSellerName'
_seller_tag_css_name2 = 'a-spacing-small olpSellerName'
_my_name = 'huahuakq'
_url = ''
_headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
'Accept-Encoding':'gzip, deflate, sdch',
'Accept-Language':'en-US,en;q=0.8,zh-CN;q=0.6',
'Cache-Control':'max-age=0',
'Connection':'keep-alive',
'Host':'',
'Referer':'',
'Upgrade-Insecure-Requests':'1',
'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36'}

class Round2Float(float):
    def __new__(cls, num):
        num = round(num, 2)
        return float.__new__(Round2Float, num)

def print_top_seller(asin):
    html = _get_html_content(asin)
    sales_list = _get_sales_list(html)[:5]
    my_position, my_price = _get_my_position(sales_list)
    # top = sales_list[0]
    # print(len(sales_list))
    first = sales_list[0][-1] if len(sales_list) > 0 else None
    second = sales_list[1][-1] if len(sales_list) > 1 else None
    print(asin, [first, second], [my_position, my_price])

def print_price_list(asin):
    try:
        html = _get_html_content(asin)
        sales_list = _get_sales_list(html)[:5]
        l = ['[{}]'.format(total) if seller==_my_name else str(total) for seller, price, shipping, total in sales_list]
    except Exception as e:
        l = [str(e)]
    print(asin, ', '.join(l))

def _get_html_content(asin):
    url = _url.format(asin)
    # print(url)
    r = requests.get(url, headers=_headers)
    # print(r.status_code)
    if r.status_code != 200:
        raise Exception('fail to get html content')
    return r.text

def _get_sales_list(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    sales_div_list = soup.find_all('div', class_=_sales_div_css_name)
    sales_list = []
    for i, sales_div in enumerate(sales_div_list):
        price = sales_div.find_all('span', class_=_price_div_css_name)[0].string
        price = _price_to_num(price)
        shipping_fee_tag = sales_div.find_all('span',
                class_=_shippingfee_tag_css_name)
        if shipping_fee_tag:
            shipping_fee = shipping_fee_tag[0].string
        else:
            shipping_fee = '0.00'
        shipping_fee = _price_to_num(shipping_fee)
        seller_tag_temp = sales_div.find_all('h3', class_=_seller_tag_css_name)
        if not seller_tag_temp:
            seller_tag_temp = sales_div.find_all('h3', class_=_seller_tag_css_name2)
        seller_tag = seller_tag_temp[0]
        seller_a = seller_tag.find_all('a')[0]
        seller_name = seller_a.string or i
        sales_list.append([seller_name, price, shipping_fee, Round2Float(price + shipping_fee - 1.99)])
    return sales_list

def _get_my_position(sales_list):
    for i, sales in enumerate(sales_list):
        if sales[0] == _my_name:
            return i + 1, sales[3]
    return -1, None

def _price_to_num(price):
    price = price.strip()
    return Round2Float(float(price[1:] if price[0] == '$' else price))

if __name__ == '__main__':
    # print_price_list('B00WG0LGBE')
    # exit()

    l = []
    for item in l:
        print_price_list(item)
        time.sleep(1)
