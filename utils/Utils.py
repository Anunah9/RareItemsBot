import os
import subprocess
import sys
import urllib.parse
import requests


def convert_price(price):
    return float(price.split(' ')[0].replace(',', '.'))


def restart_program():
    python = sys.executable
    os.execl(python, python, *sys.argv)


def convert_name(market_hash_name):
    return urllib.parse.quote(market_hash_name)


def get_pid_server():
    with open(r'C:\Users\Sasha\Desktop\CSGOFloatInspect\node_pid.txt') as f:
        pid = f.read()
        return pid


def close_server():
    pid = get_pid_server()
    print(f'PID запущенного процесса: {pid}')
    print('Выключаю сервер...')
    r = subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], shell=True, stdout=subprocess.PIPE, text=True, encoding='cp866')
    text = r.stdout
    if text:
        process_id = text.split('процесса ')[1].split(',')[0]
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process_id)], shell=True, stdout=subprocess.PIPE, text=True,
                       encoding='cp866')
    print('Сообщение: ', r.stdout)


def close_bot(pid):
    print(f'PID запущенного процесса: {pid}')
    print('Выключаю бота...')
    r = subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], shell=True, stdout=subprocess.PIPE, text=True,
                       encoding='cp866')
    text = r.stdout
    if text:
        process_id = text.split('процесса ')[1].split(',')[0]
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process_id)], shell=True, stdout=subprocess.PIPE, text=True,
                       encoding='cp866')
    print('Сообщение: ', r.stdout)


class Currensy:
    rates = {
        'cny': None,
        'usd': None,
        'rub': None
    }

    def __init__(self):
        self.rates['CNY'] = self.get_steam_currency('CNY')
        self.rates['USD'] = self.get_steam_currency('USD')
        self.rates['RUB'] = self.get_steam_currency('RUB')

    def change_currency(self, start_currency, target_currency, price):
        st_currency = self.rates[start_currency]
        tar_currency = self.rates[target_currency]
        currency = tar_currency/st_currency
        return price * currency

    def get_steam_currency(self, target_currency):
        url = f'https://api.steampowered.com/ISteamEconomy/GetAssetPrices/v1/?format=json&amp&appid=1764030&amp&key' \
              f'=97F914FB6333AC5416AF882DA9909A35'
        response = requests.get(url).json()
        currency = response['result']["assets"][0]['prices'][target_currency]/100
        return currency
