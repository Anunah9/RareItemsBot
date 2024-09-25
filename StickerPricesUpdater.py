import sqlite3
from urllib.parse import unquote
import requests
from bs4 import BeautifulSoup


def add_to_db(sticker_name, price, cur):
    sticker_name = sticker_name.replace('&#39', "'")
    query = f'INSERT INTO CSMoneyStickerPrices VALUES ("{sticker_name}", {price})'
    cur.execute(query)


def get_all_sticker_prices(cur):
    url = 'https://www.csgo.exchange/prices/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml')
    items = soup.find('tbody', class_='contentItems')
    stickers = items.findAll('tr', attrs={'data-type': ' Sticker '})
    print(len(stickers))
    for sticker in stickers:
        sticker_name = unquote(sticker['data-name'])
        price = float(sticker['data-vn'])
        add_to_db(sticker_name, price, cur)
        # print(sticker_name)
        # print(price)


def get_all_sticker_prices_v2():
    url = 'https://www.csbackpack.net/api/items?page=1&max=300000&price_real_min=0&price_real_max=100000&item_group' \
          '=sticker'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/122.0.0.0 YaBrowser/24.4.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers).json()
    return response

def main():
    db = sqlite3.connect('db/CS.db')
    cur = db.cursor()
    print('11')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/122.0.0.0 YaBrowser/24.4.0.0 Safari/537.36'
    }
    for try_ in range(5):
        # try:
            print(requests.get('https://www.csbackpack.net', headers=headers))
            currency = requests.get('https://www.csbackpack.net/api/currency/list', headers=headers).json()['rates'][
                'RUB']
            print(currency)
            stickers = get_all_sticker_prices_v2()
            break
        # except Exception as exc:
        #     print(exc)
    for sticker in stickers:
        sticker_name = sticker['markethashname']
        # print(sticker)
        sticker_price = sticker['pricelatest'] * currency
        if sticker['sold30d'] > 10:
            add_to_db(sticker_name, round(sticker_price, 2), cur)

    db.commit()
    db.close()
    print('Цены обновлены.')


if __name__ == '__main__':

    main()

