#!/usr/bin/env python3
import requests
import os
import time
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BASE_ENDPOINT = os.getenv('BASE_ENDPOINT')
HEADER = {
    'X-MBX-APIKEY': API_KEY
}

EXLUDED_COINS = ['BTC', 'ETH', 'SXP']

# copied from bot
def generate_signature(payload):
        # generate message
        message = ''
        for k in payload:
            message += '{}={}&'.format(k, str(payload.get(k)))
        # remove final '&'
        message = message[:-1]

        # generate signature
        return hmac.new(bytes(SECRET_KEY , 'latin-1'), msg = bytes(message , 'latin-1'), digestmod = hashlib.sha256).hexdigest()

payload = {
    'timestamp': int(round(time.time() * 1000))
}
payload.update({'signature': generate_signature(payload)})

current_coins_res = requests.get(BASE_ENDPOINT +  '/api/v3/account',  headers=HEADER, params=payload).json()
current_coins = [coin for coin in current_coins_res['balances'] if float(coin['free']) != 0]
# print(current_coins)

current_bnb_balance = 0

for coin in current_coins:
    coin_name = coin['asset']

    if coin_name == 'BNB':
        current_bnb_balance += float(coin['free'])
        continue
    # skip some coins
    if coin_name in EXLUDED_COINS:
        # print('Exluding %s' %(coin['asset']))
        continue

    # get value of coin in BNB
    symbol_name = coin['asset'] + 'BNB'
    payload = {
            'symbol': symbol_name
        }
    symbol_price = requests.get(BASE_ENDPOINT + '/api/v3/ticker/price', params=payload).json()['price']
    estimated_quote_value = float(coin['free']) * float(symbol_price)
    current_bnb_balance += estimated_quote_value

print(current_bnb_balance)