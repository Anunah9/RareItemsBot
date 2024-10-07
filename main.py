import asyncio
import datetime
import json
import math
import os
import sqlite3
import statistics
import subprocess
import sys
import threading
import time
import aiohttp
import bs4
import requests
import steampy
from steampy import models, exceptions
import telebot
import StickerPricesUpdater
from utils import SteamMarketAPI, Utils
from utils.OpenVPN_API_Refactor import VPN

"""Модуль отслеживания предметов:
-Взять предметы из бд
-Пройтись по каждому и выполнить следующее:
    -Узнать цену предмета
    -Узнать какие наклейки есть, их потертость и их цену
    -Если цены на наклейки приемлимые и наклейки не стертые то
        -Посмотреть переплату за эти наклейки на кс мани (сложный пункт с ним будем разбираться в модуле по работе 
        с площадками)
        -Если переплата больше чем минимальный процент профита
        -Купить предмет"""




def get_items_from_db():
    cur = params.cs_db.cursor()
    query = 'SELECT * FROM itemsForTrack'
    return cur.execute(query).fetchall()


def get_item_float_and_stickers(inspect_link):
    print('Количество ошибок: ', params.get_float_error_counter)
    url = 'http://192.168.0.14:80/'
    params_ = {
        'url': inspect_link
    }
    response = requests.get(url, params=params_)
    if response.status_code != 200:
        print('Get float and stickers:', response)
        for test in range(10):
            response = requests.get(url, params=params_)
            print('Test inspect сервера: ', test)
            if response.status_code != 200:
                params.get_float_error_counter += 1
            time.sleep(0.5)
    elif response.status_code == 200:
        params.get_float_error_counter = 0
    if params.get_float_error_counter > 7:
        response = requests.get(url, params=params_)
        if response.status_code != 200:
            # reconnect_vpn()
            # restart_program()
            print(f'Сервер стикеров не отвечает: {response.status_code}')
            # params.bot_error_logger.send_message(368333609, f'Сервер стикеров не отвечает: {response.status_code}')
            time.sleep(2)

        params.get_float_error_counter = 0
    response = response.json()
    iteminfo = response['iteminfo']
    float_item = iteminfo['floatvalue']
    stickers = iteminfo['stickers']
    stickers_result = []
    for sticker in stickers:
        if 'wear' in sticker:
            continue
        stickers_result.append({'slot': sticker['slot'], 'name': 'Sticker | ' + sticker['name']})

    return float_item, stickers_result


def get_sticker_price(sticker_names):
    handled_stickers = []
    for sticker in sticker_names:
        sticker_price1 = get_sticker_prices(sticker)
        sticker['price'] = round(sticker_price1, 2)
        handled_stickers.append(sticker)
    return handled_stickers


def get_sticker_prices(sticker):
    sticker_name = sticker['name']
    try:
        price = params.stickers_prices[sticker_name]
    except KeyError:
        print("No sticker price")
        price = 0
    return price


def add_to_checked(item_name, item_id):
    cur = params.cs_db.cursor()
    query = f'INSERT INTO checkedSteam (item_id, item_name) VALUES ({item_id}, "{item_name}")'
    cur.execute(query)
    params.cs_db.commit()


def check_handled_items(item_id):
    cur = params.cs_db.cursor()
    query = f'SELECT * FROM checkedSteam WHERE item_id = {item_id}'
    check = cur.execute(query).fetchone()
    return bool(check)


def find_strics(lst):
    element_count = {}  # Создаем пустой словарь для хранения количества элементов
    for item in lst:
        name = item['name']
        if name in element_count:
            element_count[name]['count'] += 1
        else:
            element_count[name] = {'count': 1, 'price': item['price']}
    # Фильтруем элементы, оставляем только те, что встречаются 3 и более раз
    filtered_elements = {name: info for name, info in element_count.items() if info['count'] >= 3}

    return filtered_elements


def buy_item(item_name, market_id, price, fee):
    url = 'http://192.168.0.14:8000/buyItem'
    json = {
        'item_name': item_name,
        'market_id': market_id,
        'price': price,
        'fee': fee,
    }
    response = requests.post(url, json=json)
    # response = requests.get('http://192.168.0.14:8000/getBotConfig')
    print(response)
    print(response.json())
    # params.steamAccMain.steamclient.market.buy_item(item_name, market_id, price, fee, game=models.GameOptions.CS,
    #                                                 currency=models.Currency.RUB)


class Item:
    item_name = None
    item_link = None
    price_sm = None
    stickers = None
    listing_id = None
    price_no_fee = None
    float_item = None
    fee = None


def add_to_db(*args):
    item_name, listing_id, price, stickers, sum_stickers_price = args
    print(item_name, listing_id, price, stickers)
    query = f'INSERT INTO steamBuyStatistics VALUES ("{item_name}", {listing_id}, {price / 100}, {sum_stickers_price}'
    for sticker in stickers:
        query += ', "'
        query += sticker['name']
        query += '"'
    for i in range(5 - len(stickers)):
        query += ', NULL'

    query += f', {sum_stickers_price})'
    print(query)
    params.cs_db.cursor().execute(query)
    params.cs_db.commit()


def item_handler(item_obj: Item, counter):
    print(item_obj.stickers)
    print(len(item_obj.stickers))
    stickers = get_sticker_price(item_obj.stickers)
    sum_prices_stickers = sum(list(map(lambda x: x['price'], stickers)))
    strick_stickers = find_strics(stickers)
    strick_sticker_name = ''
    strick_count = 0
    strick_price = 0
    sum_price_strick = 0
    print(f'striiiiiiiiiiic: {bool(strick_stickers)}')
    if strick_stickers:
        strick_sticker_name = list(strick_stickers.keys())[0]
        strick_count = strick_stickers[strick_sticker_name]['count']
        strick_price = strick_stickers[strick_sticker_name]['price']
        sum_price_strick = strick_price * strick_count

    print('---------------------------------------------------', strick_sticker_name)
    print(strick_stickers)
    message = f"🌟 **{item_obj.item_name}** 🌟\n" \
              f"Предмет #{counter}\n" \
              f"Ссылка: {item_obj.item_link}\n" \
              f"💲 Цена SM: {item_obj.price_sm} Руб\n" \
              f"🔖 Стикеры:\n" \
              f"💲 Общая стоимость стикеров: {round(sum_prices_stickers, 2)} Руб\n"
    for sticker in stickers:
        message += f"   • {sticker['name']} - 💲 Цена: {sticker['price']} Руб\n" \
            # f"        📈 Переплата min: {sticker['min_overpay']} Руб\n" \
        # f"        📈 Переплата max: {sticker['max_overpay']} Руб\n"
    if strick_stickers:
        message += f"🌟 **Стрики из стикеров** 🌟\n" \
                   f"💲 Общая стоимость стрика: {round(sum_price_strick, 2)} Руб\n" \
                   f"   • {strick_sticker_name} - 💲 Цена: {strick_price} Руб\n" \
                   f"      Количество - {strick_count} \n"
    print(message)

    try:

        if sum_prices_stickers > item_obj.price_sm * mult_for_common_item:
            if autobuy:
                buy_item(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee, item_obj.fee)
                add_to_db(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee, stickers,
                          round(sum_prices_stickers, 2))
            elif autobuy or send_info:
                params.bot.send_message(368333609, message)  # Я
        if strick_count == 3 and strick_count >= min_stickers_in_strick:
            if sum_price_strick > item_obj.price_sm * mult_for_strick_3 and sum_prices_stickers > min_limit_strick_price:
                if autobuy:
                    buy_item(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee,
                             item_obj.fee)
                    add_to_db(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee, stickers,
                              round(sum_prices_stickers, 2))
                elif autobuy or send_info:
                    params.bot.send_message(368333609, message)  # Я
        elif strick_count >= 4:
            if sum_price_strick > item_obj.price_sm * mult_for_strick_4 and sum_prices_stickers > min_limit_strick_price:
                if autobuy:
                    buy_item(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee,
                             item_obj.fee)
                    add_to_db(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee, stickers,
                              round(sum_prices_stickers, 2))
                # Улучшенный вариант сообщения
                elif autobuy or send_info:
                    params.bot.send_message(368333609, message)  # Я
    except steampy.exceptions.ApiException as exc:
        print(exc)
        params.bot.send_message(368333609, exc)  # Я
    except Exception as exc:
        print(exc)
        params.bot.send_message(368333609, exc)  # Я


def items_iterator(item_name, item_link, listings):
    item_obj = Item()
    item_obj.item_name = item_name
    item_obj.item_link = item_link
    counter = 0

    for key in listings.keys():
        counter += 1
        if check_handled_items(key):
            continue
        print(f'listing №{counter}')
        add_to_checked(item_name, key)
        item = listings[key]
        print(item)
        item_obj.listing_id = item['listingid']
        try:
            item_obj.price_no_fee = item['converted_price']
            item_obj.fee = item['converted_fee']
            price_sm = (item_obj.price_no_fee + item_obj.fee) / 100
            item_obj.price_sm = price_sm

            inspect_link = item['asset']['market_actions'][0]['link'].replace('%listingid%', key).replace(
                '%assetid%',
                item['asset']['id'])
        except KeyError:
            return False
        ##########################################################################################################
        print(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee, item_obj.fee)
        buy_item(item_obj.item_name, item_obj.listing_id, item_obj.price_no_fee + item_obj.fee, item_obj.fee)
        print('TEST REQUEST TEST REQUEST TEST REQUEST')
        time.sleep(100)
        ##########################################################################################################
        try:
            float_item, stickers = get_item_float_and_stickers(inspect_link)
        except KeyError as exc2:
            float_item, stickers = 2, []
            print(f'Get Float Failed: {exc2}')
        if not stickers:
            continue
        item_obj.stickers = stickers
        item_obj.float_item = float_item
        print(stickers)
        item_handler(item_obj, counter)


def update_csm_prices_in_db(item_name, price):
    query = f'UPDATE itemsForTrack SET price = {price} WHERE market_hash_name = "{item_name}"'
    params.cs_db.cursor().execute(query)
    params.cs_db.commit()


def try_login(login, password, path_mafile):
    while True:
        try:
            steamAcc = SteamMarketAPI.SteamMarketMethods(login, password, path_mafile)
            params.bot_error_logger.send_message(368333609, f'Создание экземпляра steamAcc {login} успешно')  # Я
            return steamAcc
        except ConnectionError:
            params.bot_error_logger.send_message(368333609, 'Ошибка Connection error, пробую снова')  # Я
            time.sleep(5)
        except exceptions.CaptchaRequired:
            params.bot_error_logger.send_message(368333609, 'Ошибка Captcha required, перезагружаю роутер')  # Я
            params.vpn.reconnect_vpn()
        except Exception as exc2:
            params.bot_error_logger.send_message(368333609, f'Ошибка try login: {exc2}')
            params.vpn.reconnect_vpn()


class Params:

    def __init__(self):
        self.bot_error_logger = None
        self.connected = None
        
        self.cs_db = sqlite3.connect('./db/CS.db')
        self.t_before_429 = None
        self.steamAccMain = None
        self.steamAccServer = None
        # self.reset_router = resetRouter.ResetRouter()
        self.currency = Utils.Currensy()
        self.get_float_error_counter = 0
        self.stickers_prices = self.cs_db.cursor().execute('SELECT * FROM CSMoneyStickerPrices').fetchall()
        self.first_start = True
        self.counter_requests = 0
        self.error_counter = 0
        self.counter_for_too_many_request = 0
        self.vpn = None

    def update_stickers_prices(self):
        StickerPricesUpdater.main()

    def convert_stickers_to_dict(self):
        sticker_prices_dict = {}
        for sticker in self.stickers_prices:
            sticker_prices_dict[sticker[0]] = sticker[1]
        self.stickers_prices = sticker_prices_dict

    def determination_of_initial_parameters(self):
        self.vpn = VPN(None)
        self.vpn.kill_old_vpn_connections()
        # self.bot_error_logger.send_message(368333609, 'Обновление цен на стикеры')
        self.update_stickers_prices()
        # self.connected = self.vpn.reconnect_before_connect_to_good_config()
        self.bot = telebot.TeleBot(API)
        self.bot_error_logger = telebot.TeleBot(API_ErrorLogger)
        self.bot_error_logger.send_message(368333609, 'Готово')
        self.bot_error_logger.send_message(368333609, 'Запуск VPN')  # Я
        
        if self.connected:
            self.bot_error_logger.send_message(368333609, 'VPN запущен успешно')
        self.bot_error_logger.send_message(368333609, 'Запуск бота')  # Я
        self.steamAccMain = try_login('Sanek0904', 'Bazaranet101', 'maFiles/Sanek0904.txt')
        # self.steamAccServer = try_login('abinunas1976', 'PQIUZmqgCW1992', './ServerAcc.txt')
        self.bot_error_logger.send_message(368333609,
                                           f'Авторизация в стиме: {params.steamAccMain.steamclient.is_session_alive()}')  # Я
        print(params.steamAccMain.steamclient.is_session_alive())
        self.bot_error_logger.send_message(368333609, 'Запуск inspect сервера')  # Я
        get_item_float_and_stickers('steam://rungame/730/76561202255233023/+csgo_econ_action_preview'
                                    '%20S76561198163222057A29260535484D5072782033785464255')


def read_config(file_path):
    config = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            config[key] = value
    return config


def start_cs_inspect_server():
    server_path = r'C:\Users\Sasha\Desktop\CSGOFloatInspect'
    indexjs_path = os.path.join(server_path, 'index.js')
    print('Запускаю сервер...')
    try:
        p1 = subprocess.Popen(['start', 'cmd', '/k', 'cd', server_path, '^&', 'node', indexjs_path], shell=True)
        time.sleep(15)
    except Exception as e:
        print(f'Произошла ошибка при запуске сервера: {str(e)}')


async def create_async_session(steamclient):
    headers = steamclient._session.headers  # Можете передать заголовки из вашей существующей сессии
    cookie_jar = steamclient._session.cookies
    print('ccccccccccc', cookie_jar.get_dict("steamcommunity.com"))
    async_session = aiohttp.ClientSession(headers=headers, cookies=cookie_jar.get_dict("steamcommunity.com"))
    return async_session


async def get_listings_from_response(response_text):
    soup = bs4.BeautifulSoup(response_text, 'lxml')
    info = soup.findAll('script', type="text/javascript")[-1]
    result_sting = info.text.split('g_rgListingInfo =')[1].split(';')[0]
    item_name = info.text.split('"market_hash_name":"')[1].split('","market_actions"')[0]
    print(item_name)
    listings = json.loads(result_sting)
    return item_name, listings


def response_429_handler():
    if params.counter_for_too_many_request == 0:
        result_time = time.time() - params.t_before_429
        params.t_before_429 = time.time()
        try:
            params.bot_error_logger.send_message(368333609, 'Ошибка 429')  # Я
            params.bot_error_logger.send_message(368333609,
                                                 f'Бот проработал: {result_time} секунд')  # Я
            params.bot_error_logger.send_message(368333609, f'Сделано запросов: {params.counter_requests}')  # Я
            if params.counter_for_too_many_request >= 40:
                params.bot_error_logger.send_message(368333609, 'Меняю VPN')
        except Exception as exc:
            print(exc)

        params.counter_requests = 0
        # if result_time > 3500:
        # params.bot_error_logger.send_message(368333609, 'Перезагружаю роутер')
        # params.vpn.reconnect_vpn()

    if params.counter_for_too_many_request >= 40:
        # params.bot_error_logger.send_message(368333609,
        #                                      f'Счетчик 429: {params.counter_for_too_many_request}')  # Я
        # Utils.close_server()
        # params.bot_error_logger.send_message(368333609, 'Перезагружаю роутер')
        params.cs_db.cursor().execute(
            f'INSERT INTO dead_vpn VALUES ("{params.vpn.config_name}", "{datetime.datetime.now()}")')
        params.cs_db.commit()
        params.vpn.reconnect_vpn()
    params.counter_for_too_many_request += 1


async def fetch_data(session: aiohttp.ClientSession, item, counter):
    url = item[1]
    delay = 0.85 * counter
    await asyncio.sleep(delay)
    session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, ' \
                                    'like Gecko) Chrome/106.0.0.0 YaBrowser/22.11.2.807 Yowser/2.5 ' \
                                    'Safari/537.36'
    session.headers['Referer'] = params.steamAccMain.headers['Referer']
    t1 = time.time()
    try:
        response = await session.get(url, timeout=10)
        params.error_counter = 0
    except aiohttp.ClientError as e:
        print(f'Error counter: {params.error_counter}')
        params.error_counter += 1
        if params.error_counter >= 40:
            params.error_counter = 0
            params.vpn.reconnect_vpn()

        print(f'Error during request to {url}: {e}')
        return

    except asyncio.exceptions.TimeoutError:
        print('Timeout Error')
        params.error_counter += 1
        if params.error_counter >= 40:
            params.error_counter = 0
            params.vpn.reconnect_vpn()
        return

    print('Время одного запроса: ', time.time() - t1)
    params.counter_requests += 1
    if response.status == 200:
        params.counter_for_too_many_request = 0
        try:
            data = await response.text()
            item_name, listings = await get_listings_from_response(data)
            params.vpn.requests_list.append(time.time() - t1)
        except aiohttp.client_exceptions.ClientPayloadError as exc:
            print(exc)
            print('-----------------------------------')
            print(response)
            print(response.status)
            listings = {}
        except asyncio.exceptions.TimeoutError as exc:
            print(exc)
            print('-----------------------------------')
            print(response)
            print(response.status)
            listings = {}
        if listings:
            items_iterator(item_name, url, listings)
        else:
            print(f'Listings: {listings}')
    else:
        print(f'Error response from {url}: {response.status}')
        if response.status == 429:
            response_429_handler()


def check_country():
    country = params.cs_db.cursor().execute('SELECT vpn_country FROM flags').fetchone()[0]
    print('Текущая страна: ', country)
    if country == 'Russian Federation':
        params.vpn.reconnect_vpn()


async def main():
    session = await create_async_session(steamclient=params.steamAccMain.steamclient)
    start = 0
    while True:
        items = get_items_from_db()
        items = [('fsdf', 'https://steamcommunity.com/market/listings/730/Desert%20Eagle%20%7C%20Corinthian%20%28Field-Tested%29')]
        check_country()
        print('Количество предметов: ', len(items))
        for item in items:
            print(item[0])

        print('---------------------------------------')
        tasks1 = []
        counter = 0
        iter_time = round(60 / len(items))
        print('Кол-во секунд на полную итерацию', iter_time)

        for i in range(iter_time):
            for item in items:
                tasks1.append(fetch_data(session, item, counter))
                counter += 1
        t2 = time.time()
        await asyncio.gather(*tasks1)
        result_time = time.time() - t2
        target_delay = 60 - result_time
        print('Время выполенения запросов: ', result_time)
        print('Задержка до нужного времени: ', target_delay)
        print('Количество выполненных запросов: ', counter)
        t3 = time.time()
        await asyncio.sleep(target_delay if target_delay > 0 else 0)
        print('Проверка задержки: ', time.time() - t3)
        print('-----------------------------------------')
        params.vpn.vpn_config_requests_information()
        params.vpn.cycle += 1


def print_hel(*args):
    pid = os.getpid()
    cs_db = sqlite3.connect('./db/CS.db')
    cur = cs_db.cursor()
    ip = None
    country = None
    while True:
        time_now = time.time()
        for i in range(5):
            try:
                info = make_test_requests('https://api.myip.com')
                ip = info['ip']
                country = info['country']
                break
            except requests.exceptions.ConnectionError:
                time.sleep(1)
                continue
        if ip and country:
            query = f'UPDATE flags SET vpn_ip="{ip}", ' \
                    f'vpn_country="{country}"'
            cur.execute(query)
            print(query)
        if country == 'Russian Federation':
            params.vpn.reconnect_vpn()
        ip = None
        country = None
        query = f'UPDATE flags SET working_time_check={int(time_now)}, pid_bot={pid}'
        cur.execute(query)
        cs_db.commit()
        time.sleep(20)


def make_test_requests(url):
    response = requests.get(url)
    print(response)
    if response.status_code == 200:
        print(response.json())
        return response.json()
    else:
        print('Произошла ошибка, строка 526, функция make_test_response()')
        return


if __name__ == '__main__':
    API = '5096520863:AAHHvfFpQTH5fuXHjjAfzYklNGBPw4z57zA'
    API_ErrorLogger = '6713247775:AAEq_pT350E8rUuyaz8eSWvyMYawK1Iqz9c'
    params = Params()
    params.determination_of_initial_parameters()
    t1 = threading.Thread(target=print_hel, args=('bob',), daemon=True)
    # t1.start()
    make_test_requests('https://api.myip.com')
    params.convert_stickers_to_dict()
    # print(params.stickers_prices)
    config = read_config('configSteam.txt')

    mult_for_strick_3 = float(config.get('MULT_FOR_STRICK_3'))
    mult_for_strick_4 = float(config.get('MULT_FOR_STRICK_4'))
    min_stickers_in_strick = int(config.get('MIN_STICKERS_IN_STRICK'))
    mult_for_common_item = float(config.get('MULT_FOR_COMMON_ITEM'))

    send_info = True
    test_params = False
    if test_params:
        autobuy = False
    else:
        autobuy = config.get('AUTOBUY')
    min_limit_strick_price = int(config.get('MIN_LIMIT_PRICE_FOR_STRICK'))
    setting_message = f"**Текущие настройки бота** \n" \
                      f"Текущий баланс💲: {0} Руб\n" \
                      f"Коэффициенты для стоимости стрика: {mult_for_strick_3}\n" \
                      f"Коэффициенты для стоимости без стрика: {mult_for_common_item}\n" \
                      f"Автопокупка: {autobuy}\n"

    params.bot_error_logger.send_message(368333609, setting_message)  # Я
    params.t_before_429 = time.time()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
