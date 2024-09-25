import asyncio
import datetime
import os
import random
import sqlite3
import statistics
import subprocess
import time
from pathlib import *
import aiohttp
import requests
from dateutil import parser


class VPN:
    connected = False
    disconnect = False
    process = None
    test_url = None
    path_configs = r'C:\Users\Sasha\Desktop\openVpn\configs'
    current_ip = None

    def __init__(self, test_url=None):
        self.config_name = None
        self.test_url = test_url
        self.cs_db = self.db_connect()
        self.requests_list = []
        self.cycle = 0

    def vpn_config_requests_information(self):
        if not self.requests_list:
            print('Нет данных о запросах')
            return
        request_count = len(self.requests_list)
        mean_time_one_request = round(statistics.mean(self.requests_list), 2)
        median_time_one_request = round(statistics.median(self.requests_list), 2)
        min_time_request = round(min(self.requests_list), 2)
        max_time_request = round(max(self.requests_list), 2)
        mean_counter_request_per_cycle = round(request_count / (self.cycle + 1), 2)
        query = f'UPDATE vpn_configs_debug_info SET cycles={self.cycle},' \
                f' mean_time_request={mean_time_one_request},' \
                f' median_time_request={median_time_one_request},  min_time_request={min_time_request},' \
                f' max_time_request={max_time_request}, mean_counter_request={mean_counter_request_per_cycle} ' \
                f' WHERE name="{self.config_name}"'
        print(query)
        self.cs_db.cursor().execute(query)
        self.cs_db.commit()
        print('Cycle: ', self.cycle)
        print('Количество выполненных запросов: ', request_count)
        print('Среднее время выполнение запроса: ', mean_time_one_request)
        print('Медианное время выполнение запроса: ', median_time_one_request)
        print('Минимальное время выполнение запроса: ', min_time_request)
        print('Максимальное время выполнение запроса: ', max_time_request)
        print('Среднее количество выполненных запросов на цикл: ', mean_counter_request_per_cycle)

    def reconnect_vpn(self):
        print('---------------------------------')
        print('Reconnect VPN')
        print('---------------------------------')
        self.cycle = 0
        self.requests_list = []
        self.disconnect_vpn()
        self.kill_old_vpn_connections()
        self.reconnect_before_connect_to_good_config()

    @staticmethod
    def db_connect():
        if __name__ == '__main__':
            db_name = '../db/CS.db'
        else:
            db_name = './db/CS.db'
        return sqlite3.connect(db_name)

    def connect_to_vpn(self, config_path: Path):
        args = [r'C:\Program Files\OpenVPN\bin\openvpn.exe',
                '--config',
                config_path]
        shell = fr'"C:\Program Files\OpenVPN\bin\openvpn.exe" --config "{config_path}" '
        # shell_linux = subprocess.Popen(["sudo", "openvpn", "--config", config_path])
        self.process = subprocess.Popen(
            shell, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE
        )

    def get_config_files(self):
        files = os.listdir(self.path_configs)
        return files

    def connect_to_random_config(self):
        configs = self.get_config_files()
        random_config = configs[random.randrange(0, len(configs))]
        self.config_name = random_config

        dead_config_invalid = self.cs_db.cursor().execute(f'SELECT * FROM vpn_configs_debug_info WHERE name="{self.config_name}" AND invalid_check=1').fetchone()
        if dead_config_invalid:
            last_check = parser.parse(dead_config_invalid[3])
            if datetime.datetime.now() - last_check < datetime.timedelta(minutes=30):
                # print('Invalid VPN')
                return

        # print(f'SELECT * FROM dead_vpn WHERE config_name="{self.config_name}"')
        dead_config_429 = self.cs_db.cursor().execute(f'SELECT * FROM dead_vpn WHERE config_name="{self.config_name}"').fetchone()
        # print(dead_config_429)
        if dead_config_429:
            last_check = parser.parse(dead_config_429[1])
            if datetime.datetime.now() - last_check < datetime.timedelta(minutes=30):
                return

        config_path = Path(self.path_configs, random_config)
        print(config_path)
        self.connect_to_vpn(config_path)
        time.sleep(15)

        check = self.__check_connection__()
        if check:
            self.connected = True

    def reconnect_before_connect_to_good_config(self):
        print(f'Start reconnecting: {datetime.datetime.now()}')

        self.cs_db.cursor().execute(f'UPDATE flags SET start_reconnect="{datetime.datetime.now()}"')
        self.cs_db.commit()
        while not self.connected:
            self.connect_to_random_config()
        self.cs_db.cursor().execute(f'UPDATE flags SET end_reconnect="{datetime.datetime.now()}"')
        print(f'End reconnecting: {datetime.datetime.now()}')
        self.cs_db.commit()
        return True
    
    @staticmethod
    def kill_old_vpn_connections():
        subprocess.Popen('Taskkill /IM openvpn.exe /F')
        time.sleep(5)

    def disconnect_vpn(self):
        print('Выполняюю выключение')
        self.process.terminate()
        self.process.wait(timeout=5)
        self.connected = False

    def __check_connection__(self, test_url=None, ):
        if __name__ == '__main__':
            db_name = '../db/CS.db'
        else:
            db_name = './db/CS.db'

        print('Запускаю проверку VPN')

        try:
            info = make_test_requests('https://api.myip.com')
        except requests.exceptions.ConnectionError:
            return False
        if info:
            ip = info['ip']
            country = info['country']
            print(ip, country)
            if country != 'Russian Federation':
                print('123123')
                self.cs_db.cursor().execute(f'UPDATE flags SET pid_vpn_service={self.process.pid}')
                self.cs_db.commit()
                self.current_ip = ip
                to_db(self.config_name, ip, country, datetime.datetime.now(), False, self.cs_db)
                return True
        print('Выполняю отключение VPN')
        to_db(self.config_name, None, None, datetime.datetime.now(), True, self.cs_db)
        self.process.terminate()
        self.process.wait(timeout=5)
        return False


def to_db(config_name_, ip, country, last_check_time, invalid, db: sqlite3.Connection):
    query = F'INSERT INTO vpn_configs_debug_info (name, ip, country, last_check_time, invalid_check) VALUES ' \
            F'("{config_name_}", "{ip}", "{country}", "{last_check_time}", {invalid})'
    print(query)
    db.cursor().execute(query)
    db.commit()


async def main(vpn_obj: VPN):
    print("Начинаю проверку соединения")

    for i in range(2):
        t1 = time.time()
        async with aiohttp.get('https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Elite%20Build%20('
                               'Minimal%20Wear)') as response:
            print(response.status)
            # print(await response.text())
        t2 = time.time() - t1
        print('Время выполнения s1: ', t2)
        vpn.disconnect_vpn()
        return True


def make_test_requests(url):
    headers = {
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/126.0.0.0 YaBrowser/24.7.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    print(response)
    if response.status_code == 200:
        print(response.json())
        return response.json()
    else:
        print('Произошла ошибка, строка 144, функция make_test_response()')
        return


def main1():
    print('hello')
    while True:
        try:
            t1 = time.time()
            info = make_test_requests('https://api.myip.com')
            if info:
                if info['country'] == 'Russian Federation':
                    vpn.connect_to_random_config()
                print('Время выполнения запроса: ', time.time() - t1, 'секунд')
            time.sleep(1)
        except KeyboardInterrupt:
            print('Завершаю работу программы')
            vpn.disconnect_vpn()
            break

    # vpn.disconnect_vpn()


if __name__ == '__main__':
    path_to_config_folder = r'C:\Users\Sasha\Desktop\openVpn\configs'
    config_name = '219.100.37.163_tcp_443.ovpn'
    result_path = path_to_config_folder + "\\" + config_name
    print(result_path)
    vpn = VPN('https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Slate%20%28Field-Tested%29')
    con = sqlite3.connect('../db/CS.db')
    # vpn.connect_to_vpn(result_path)
    # vpn.connect_to_random_config()
    # vpn.reconnect_before_connect_to_good_config()
    # vpn.disconnect_vpn()
    vpn.kill_old_vpn_connections()
    # asyncio.get_event_loop().run_until_complete(main(vpn))

    # main1()
