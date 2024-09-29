import ast
import datetime
import json
import pprint
import time

import aiohttp
import numpy as np
from statistics import median
import pickle

import requests.exceptions
import steampy.models
import steampy.guard
from steampy.client import SteamClient
from bs4 import BeautifulSoup
from utils import Utils


class TooManyRequestsException(Exception):
    def __str__(self):
        return f"Слишком много запросов."


class SteamMarketMethods:
    steamclient: steampy.client.SteamClient = None
    async_session = None
    headers = {
        'Referer': 'https://steamcommunity.com/market/listings/730/',
        'User-Agent': 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/106.0.0.0 YaBrowser/22.11.2.807 Yowser/2.5 Safari/537.36 '
    }

    def __init__(self, login, password, path_mafile):
        print('load')

        self.login = login
        self.password = password
        self.path_mafile = path_mafile
        # self.write_login()
        self.steamclient = self.load_login(path_login_file='maFiles/Sanek0904.bin')
        print(self.steamclient.is_session_alive())
        if not self.steamclient.is_session_alive():
            print('write')
            self.write_login()

            if not self.steamclient.is_session_alive():
                print('Не получилось ')


    @staticmethod
    def load_login(path_login_file: str) -> steampy.client.SteamClient:
        print('Load ffffafa', path_login_file)
        with open(path_login_file, 'rb') as f:
            return pickle.load(f)

    def write_login(self):
        self.steamclient = SteamClient('97F914FB6333AC5416AF882DA9909A35')
        self.steamclient.login(self.login, self.password, 'maFiles/Sanek0904.txt')
        print(self.steamclient)
        print(self.steamclient._session.cookies.get_dict("steamcommunity.com"))
        with open('maFiles/Sanek0904.bin', 'wb') as f:
            pickle.dump(self.steamclient, f)

    def get_steam_prices(self, item_name_id):
        """ Получаем первые две позиции по покупке и продаже"""
        url = 'https://steamcommunity.com/market/itemordershistogram?'
        headers = {
            'Referer': 'https://steamcommunity.com/market/listings/730/',
            'User-Agent': 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                          'like Gecko) Chrome/106.0.0.0 YaBrowser/22.11.3.818 Yowser/2.5 Safari/537.36 '

        }
        params = {
            'country': 'RU',
            'language': 'english',
            'currency': 5,
            'item_nameid': int(item_name_id),
            'two_factor': 0
        }
        response = self.steamclient._session.get(url, params=params, headers=headers)
        print(response)
        response = response.json()
        first_buy_price, second_buy_price, first_sell_price, second_sell_price = None, None, None, None
        try:
            first_buy_price = response['buy_order_graph'][0][0]
        except IndexError:
            pass
        except KeyError:
            print(response)
        try:
            second_buy_price = response['buy_order_graph'][1][0]
        except IndexError:
            pass
        except KeyError:
            print(response)
        try:
            first_sell_price = response['sell_order_graph'][0][0]
        except IndexError:
            pass
        except KeyError:
            print(response)
        try:
            second_sell_price = response['sell_order_graph'][1][0]
        except IndexError:
            pass
        except KeyError:
            print(response)
        print(first_buy_price, second_buy_price, first_sell_price, second_sell_price)
        return first_buy_price, second_buy_price, first_sell_price, second_sell_price

    def get_price_history(self, market_hash_name):
        url = f'https://steamcommunity.com/market/pricehistory/'
        params = {'market_hash_name': market_hash_name,
                  'appid': '730',
                  'currency': '5',
                  'format': 'json'
                  }

        response = self.steamclient._session.get(url, params=params, headers=self.headers)
        print(response.url)
        print(response)
        if response.status_code != 200:
            print(f'Get Price History: {response}')
            return None
        try:
            status = response.json()['success']
        except TypeError:
            print('Ошибка TypeError')
            return None

        price_history = self.__convert_history(response.json()['prices'])
        return price_history

    def get_item_listings_only_first_10(self, market_hash_name):

        url = 'https://steamcommunity.com/market/listings/730/' + Utils.convert_name(market_hash_name)
        response = self.steamclient._session.get(url, headers=self.headers)
        if response.status_code != 200:
            print('Get listing item', response)
            return response.status_code
        soup = BeautifulSoup(response.content, 'lxml')
        info = soup.findAll('script', type="text/javascript")[-1]
        result_sting = info.text.split('g_rgListingInfo =')[1].split(';')[0]
        listings = json.loads(result_sting)

        return listings

    async def create_async_session(self):
        headers = self.steamclient._session.headers  # Можете передать заголовки из вашей существующей сессии
        cookie_jar = self.steamclient._session.cookies
        sync_cookies = requests.utils.dict_from_cookiejar(cookie_jar)
        self.async_session = aiohttp.ClientSession(headers=headers, cookies=sync_cookies)

    async def async_get_item_listings_only_first_10(self, market_hash_name, link):
        url = 'https://steamcommunity.com/market/listings/730/' + Utils.convert_name(market_hash_name)
        response = await self.async_session.get(url)

        if response.status != 200:
            print('Get listing item', response)
            return response.status
        return (market_hash_name, link, response)

    @staticmethod
    async def get_listings_from_response( response: aiohttp.ClientResponse):
        response_text = await response.text()
        soup = BeautifulSoup(response_text, 'lxml')
        info = soup.findAll('script', type="text/javascript")[-1]
        result_sting = info.text.split('g_rgListingInfo =')[1].split(';')[0]
        listings = json.loads(result_sting)
        return listings

    async def get_item_listings_only_first_10_async(self, market_hash_name):
        url = 'https://steamcommunity.com/market/listings/730/' + Utils.convert_name(market_hash_name)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    print('Get listing item', response)
                    return response.status
                content = await response.text()
                soup = BeautifulSoup(content, 'lxml')
                info = soup.findAll('script', type="text/javascript")[-1]
                result_string = info.text.split('g_rgListingInfo =')[1].split(';')[0]
                listings = json.loads(result_string)
                return listings

    def get_item_listings(self, market_hash_name):
        """Использует ссылку по которой очень быстро банит запросы"""
        market_hash_name = Utils.convert_name(market_hash_name)
        url = f'https://steamcommunity.com/market/listings/730/{market_hash_name}/render/'
        params = {
            'start': 0,
            'count': 25,
            'country': 'RU',
            'language': 'english',
            'format': 'json',
            'currency': 5
        }
        response = self.steamclient._session.get(url, params=params, headers=self.headers)
        print('Listings:', response)
        response = response.json()
        listings = response['listinginfo']
        return listings

    def get_my_inventory(self):
        return self.steamclient.get_my_inventory(game=steampy.models.GameOptions.CS)

    def get_buy_history(self):
        url = 'https://steamcommunity.com/market/myhistory'
        params = {
            'count': 100
        }
        response = self.steamclient._session.get(url, headers=self.headers, params=params)
        print(f'Get Buy History: {response}')

        if response.status_code != 200:
            return None
        try:
            status = response.json()['success']

        except TypeError:
            return None
        return response.json()

    @staticmethod
    def __convert_history(price_history):
        for date in price_history:
            date[0] = date[0].split(' ')
            date[0] = date[0][:3]
            date[0] = ' '.join(date[0])
            date[0] = datetime.datetime.strptime(date[0], "%b %d %Y")
            date[1] = float(date[1])
            date[2] = int(date[2])
        return price_history

    @staticmethod
    def find_anomalies(price_history):
        price_history_prices = list(map(lambda price: price[1], price_history))
        price_history_without_anomalies = []
        anomalies = []
        random_data_std = np.std(price_history_prices)
        random_data_mean = np.mean(price_history_prices)
        anomaly_cut_off = random_data_std * 3

        lower_limit = random_data_mean - anomaly_cut_off
        upper_limit = random_data_mean + anomaly_cut_off

        for indx, outlier in enumerate(price_history_prices):
            if outlier < upper_limit or outlier > lower_limit:
                price_history_without_anomalies.append(outlier)
            else:
                anomalies.append(outlier)
        print('Аномалии', anomalies)
        return price_history

    @staticmethod
    def get_sales_for_days(price_history, days):
        sales = []
        now = datetime.datetime.now()
        delta = datetime.timedelta(days)
        days_date = now - delta
        for date in price_history:
            if date[0] > days_date:
                sales.append(date)
        return sales

    @staticmethod
    def peak_history(price_history):
        """Так как в истории цены смешаны продажи по автопокупке и продажи по обычной цене, возникает необходимость отделять
         их друг от друга для правильного расчета средневзвешенной цены"""
        peaks = []
        try:
            median_price = median(list(map(lambda x: x[1], price_history)))
        except:
            return []
        for date in price_history:
            if date[1] > median_price:
                peaks.append(date)
        return peaks

    @staticmethod
    def get_avg_price(price_history_peaks):
        """Количество продаж за 2 недели"""
        '''direction - Верхние или нижние пики (up, down)'''
        count_for_middle_price = 0
        cumm_price = 0
        for date in price_history_peaks:
            count_for_middle_price += date[2]
            cumm_price += date[1] * date[2]
        try:
            middle_price = cumm_price / count_for_middle_price
        except ZeroDivisionError:
            middle_price = 0
        return middle_price

    @staticmethod
    def get_count_sales(price_history):
        count = 0
        for sell in price_history:
            count += sell[2]
        return count

    @staticmethod
    def get_get_days_volatility():
        pass

    def get_clear_price_history(self, price_history_days):
        sell_prices = self.peak_history(price_history_days)
        sell_prices_without_anomalies = self.find_anomalies(sell_prices)
        return sell_prices_without_anomalies

    def create_buy_order(self, market_hash_name, price, quantity):
        url = 'https://steamcommunity.com/market/createbuyorder/'
        # print(self.steamclient._session.cookies.get('sessionid'))
        params = {
            'sessionid': self.steamclient._session.cookies.values()[0],
            'currency': 5,
            'appid': 730,
            'market_hash_name': market_hash_name,
            'price_total': price * 100,
            'quantity': quantity,
            'billing_state': '',
            'save_my_address': 0
        }
        print(params)

        response = self.steamclient._session.post(url, params, headers=self.headers)
        print(response.json())

