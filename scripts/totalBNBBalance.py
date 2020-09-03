#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')

# todo remove bot

current_balance = float(bot.get_coin_amount(symbol[len(BASE_COIN):]))
# also add every other coin from this pair to current balance to make bot run simultanioulsy
balances = bot.get_account_information()['balances']
# calc value of each base coin to quote coin value
for balance in balances:
    symbol_name = balance['asset'] + symbol[len(BASE_COIN):]
    symbol_price = bot.get_symbol_price(symbol_name)
    estimated_quote_value = float(balance['free']) * float(symbol_price)
    current_balance += estimated_quote_value
