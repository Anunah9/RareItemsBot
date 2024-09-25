import datetime
import os
import random
import sqlite3
import subprocess
import threading
import time
from pathlib import *
import aiohttp
import ifaddr
import requests
from openvpn_status.models import Client





class VPN:
    connected = False
    disconnect = False
    process = None
    test_url = None
    path_configs = r'C:\Users\Sasha\Desktop\openVpn\configs'

    def __init__(self, test_url=None):
        self.config_name = None
        self.test_url = test_url

    def get_active_sessions(self, ips):
        sessions = []
        for ip in ips:
            session = self.session_for_src_addr(ip)
            try:
                response1 = session.get('https://httpbin.org/ip')
            except requests.exceptions.ConnectionError:
                continue
            sessions.append((ip, session))
            print(response1)
        return sessions

    def session_for_src_addr(self, addr: str) -> requests.Session:
        session = requests.Session()
        for prefix in ('http://', 'https://'):
            session.get_adapter(prefix).init_poolmanager(
                connections=requests.adapters.DEFAULT_POOLSIZE,
                maxsize=requests.adapters.DEFAULT_POOLSIZE,
                source_address=(addr, 0),
            )
        return session

    def get_adapters_ips(self):
        adapters = ifaddr.get_adapters()
        ips = []
        for adapter in adapters:
            if 'TAP-Windows' in adapter.nice_name:
                print("IPs of network adapter " + adapter.nice_name)
                ips.append(adapter.ips[1].ip)
        return ips

    async def session_for_src_addr_async(self, addr: str) -> aiohttp.ClientSession:
        connector = aiohttp.TCPConnector(limit=0, local_addr=(addr, 0))
        session = aiohttp.ClientSession(connector=connector)
        return session

    async def get_active_async_sessions(self, ips):
        sessions = []
        for ip in ips:
            session = await self.session_for_src_addr_async(ip)
            try:
                response1 = await session.get('https://httpbin.org/ip')
            except aiohttp.client_exceptions.ClientConnectorError:
                continue
            sessions.append(session)
            print(response1)
        return sessions

    def connect_to_vpn(self, config_path: Path):
        args = [r'C:\Program Files\OpenVPN\bin\openvpn.exe',
                '--config',
                config_path]
        shell = fr'"C:\Program Files\OpenVPN\bin\openvpn.exe" --config "{config_path}" '
        # shell_linux = subprocess.Popen(["sudo", "openvpn", "--config", config_path])
        self.process = subprocess.Popen(
            shell, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE
        )
        while True:
            nextline = self.process.stdout.readline().decode("unicode_escape")
            print(nextline)
            if 'Initialization Sequence Completed' in nextline:
                self.connected = True
                print('Подключение выполнено успешно!')
                break
            elif self.disconnect and "is not supported by ovpn-dco, disabling data channel offload." in nextline:
                self.disconnect = False
                raise Exception('VPN Stacked')
            elif self.disconnect:
                print('disconnect')
                self.disconnect = False
                break

    def connect_to_vpn1(self, config_path: Path):
        args = [r'C:\Program Files\OpenVPN\bin\openvpn.exe',
                '--config',
                config_path]
        shell = fr'"C:\Program Files\OpenVPN\bin\openvpn.exe" --config "{config_path}" '
        # shell_linux = subprocess.Popen(["sudo", "openvpn", "--config", config_path])
        self.process = subprocess.Popen(
            shell, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE
        )
        time.sleep(15)

    def get_config_files(self):
        files = os.listdir(self.path_configs)
        return files

    def connect_to_random_config(self):
        configs = self.get_config_files()
        random_config = configs[random.randrange(0, len(configs))]
        self.config_name = random_config
        config_path = Path(self.path_configs, random_config)
        print(config_path)
        t1 = threading.Thread(target=self.__check_connection__, args=(self.test_url,))
        t1.start()
        self.connect_to_vpn(config_path)
        t1.join()

    def reconnect_before_connect_to_good_config(self):
        while not self.connected:
            self.connect_to_random_config()
        return True

    def disconnect_vpn(self):
        print('Выполняюю выключение')
        self.process.terminate()
        self.process.wait(timeout=5)
        self.connected = False

    def __check_connection__(self, test_url=None, ):
        i = 15
        # print(f'Через {i} секунд будет проверка VPN')
        # time.sleep(i)
        if __name__ == '__main__':
            db_name = '../db/CS.db'
        else:
            db_name = './db/CS.db'
        cs_db = sqlite3.connect(db_name)
        print('Запускаю проверку VPN')
        for i in range(i):
            time.sleep(1)
            print(i)
            if self.connected:
                try:
                    info = make_test_requests('https://api.myip.com')
                except requests.exceptions.ConnectionError:
                    break
                if info:
                    ip = info['ip']
                    country = info['country']
                    print(ip, country)
                    if country != 'Russian Federation':
                        print('123123')
                        cs_db.cursor().execute(f'UPDATE flags SET pid_vpn_service={self.process.pid}')
                        cs_db.commit()
                        if test_url:
                            try:
                                response = requests.get(test_url)
                                print(response)
                            except requests.exceptions.ConnectionError:
                                print('Connection error')
                                to_db(self.config_name, ip, country, datetime.datetime.now(), True, False, cs_db)
                                response = None

                            if response and response.status_code == 200:
                                to_db(self.config_name, ip, country, datetime.datetime.now(), False, False, cs_db)
                                return True
                            elif response and response.status_code == 429:
                                to_db(self.config_name, ip, country, datetime.datetime.now(), True, False, cs_db)
                        else:
                            return True
        print('Выполняю отключение VPN')
        self.disconnect = True
        self.connected = False
        to_db(self.config_name, None, None, datetime.datetime.now(), False, True, cs_db)

        self.process.terminate()
        self.process.wait(timeout=5)

        return False


def to_db(config_name_, ip, country, last_check_time, manyRequestError, invalid, db: sqlite3.Connection):
    query = F'INSERT INTO vpn_configs_debug_info VALUES ("{config_name_}", "{ip}", "{country}", "{last_check_time}", ' \
            F'{manyRequestError}, {invalid})'
    print(query)
    db.cursor().execute(query)
    db.commit()


async def main(vpn_obj: VPN):
    print('Ожидание подключения')
    while not vpn_obj.connected:
        time.sleep(1)
    print("Начинаю проверку соединения")
    ips = get_adapters_ips()
    sessions = await get_active_async_sessions(ips)
    for i in range(2):
        for session in sessions:
            t1 = time.time()
            async with session.get('https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Elite%20Build%20('
                                   'Minimal%20Wear)') as response:
                print(response.status)
                # print(await response.text())
            t2 = time.time() - t1
            print('Время выполнения s1: ', t2)
    check_end = input('Закончить выполнение?: (y/n)')
    if check_end.lower() == 'y':
        for session in sessions:
            await session.close()
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
    vpn.reconnect_before_connect_to_good_config()
    # main1()
