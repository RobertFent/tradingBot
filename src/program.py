from bot import TradingBot
from calc import Calculator
import time
import argparse
import logging
import traceback
import os
import re
from dotenv import load_dotenv

load_dotenv()

# real spot
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BASE_ENDPOINT = os.getenv('BASE_ENDPOINT')

# test spot
API_KEY_TEST = 'yCYrFohrHosLdJ34RKCLSCKp7uGkvxKRapSBw3OCnsYffL1u9j6Rmj2QkH9WN0dl'
SECRET_KEY_TEST = 'TjIYauG0aPiebGKzGzqiggeWf2895HFkYKbhZFr8YjPVu1shyRLtrauClzy21Y72'
BASE_ENDPOINT_TEST = 'https://testnet.binance.vision'

# Symbol: BASECOIN-QUOTECOIN
# SELL: sells 1 basecoin; BUY: buys 1 basecoin
BASE_COIN = os.getenv('BASE_COIN')
QUOTE_COIN = os.getenv('QUOTE_COIN')
DEFAULT_SYMBOL = BASE_COIN + QUOTE_COIN

DEFAULT_STATE = os.getenv('DEFAULT_STATE')
DEFAULT_DECIMAL_PLACES = os.getenv('DEFAULT_DECIMAL_PLACES')

# needed for later parsing
base_coin_len = len(BASE_COIN)

DEFAULT_PERCENTAGE = float(os.getenv('DEFAULT_PERCENTAGE'))

# Thresholds for buy and sell
# buy
# price decreased by given percentage
DIP_THRESHOLD = float(os.getenv('DIP_THRESHOLD'))
# price increased by given percentage
UPWARD_TREND_THRESHOLD = float(os.getenv('UPWARD_TREND_THRESHOLD'))
# sell
# price increased by given percentage
PROFIT_THRESHOLD = float(os.getenv('PROFIT_THRESHOLD'))
# price decreased by given percentage
STOP_LOSS_THRESHOLD = float(os.getenv('STOP_LOSS_THRESHOLD'))

# testing thresholds
# DIP_THRESHOLD = -0.02
# UPWARD_TREND_THRESHOLD = 0.02
# PROFIT_THRESHOLD = 0.02
# STOP_LOSS_THRESHOLD = -0.02

profit_arr = []

# todo decide where to parse float to str

def init_classes(testing, init_state, symbol):
    calc = Calculator()
    logging.info('Init bot with symbol: %s' % (symbol))
    if testing:
        bot = TradingBot(API_KEY_TEST, SECRET_KEY_TEST,
                         BASE_ENDPOINT_TEST, init_state, symbol)
    else:
        bot = TradingBot(API_KEY, SECRET_KEY,
                         BASE_ENDPOINT, init_state, symbol)
    return calc, bot


def parse_arguments():
    parser = argparse.ArgumentParser('My Trading Bot')
    parser.add_argument('symbol', type=str,
                        help='Symbol the bot shall trade', nargs='?')
    parser.add_argument('percentage', type=float,
                        help='Amount of current balance the bot shall trade', nargs='?')
    parser.add_argument('decimal_places', type=int,
                        help='Number of decimal places behind coin for trading', nargs='?')
    args = parser.parse_args()
    symbol = args.symbol if args.symbol else DEFAULT_SYMBOL
    percentage = round(args.percentage, 2) if args.percentage else DEFAULT_PERCENTAGE
    # todo parse needed?
    decimal_places = args.decimal_places if args.decimal_places else DEFAULT_DECIMAL_PLACES
    return symbol, percentage, int(decimal_places)


def get_readable_timestamp():
    return '%sh:%smin:%ssec' % (time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_sec)


def bot_loop(calc, bot, symbol, starting_balance, percentage_balance, decimal_places):
    default_price = float(bot.get_symbol_price())
    i = 0
    while True:
        current_price = float(bot.get_symbol_price())
        total_price_change = calc.get_total_change(
            current_price, default_price)
        percentage_price_change = round(
            calc.get_percentage_change(current_price, default_price), 3)

        if i % 5 == 0:
            print('\n\nTime: %s' % (get_readable_timestamp()))
            print('Total price change: %f' % (total_price_change))
            print('Percentage price change: %2.2f' % (percentage_price_change))

        if should_exit(bot, symbol, starting_balance):
            raise Exception('Time to go now')

        if do_next_action(percentage_price_change, bot, calc, symbol, current_price, percentage_balance, decimal_places):
            default_price = current_price
        time.sleep(30)
        i += 1


# returns true if current balance is twice as great or half starting balance
def should_exit(bot, symbol, starting_balance):
    current_balance = float(bot.get_coin_amount(symbol[base_coin_len:]))
    return current_balance < float(starting_balance)/2 or current_balance > float(starting_balance)*2

# todo? round needed?
def calc_trading_coins(calc, current_balance, percentage_balance, current_price, decimal_places):
    base_coins = calc.get_amount_by_percentage(percentage_balance, current_balance)
    trading_coins = round(base_coins / current_price, decimal_places)
    if (decimal_places < 1): return int(trading_coins)
    return trading_coins



def log_trade(state, bot, symbol, percentage_price_change, coins, current_avg_price):
    current_balance_base = bot.get_coin_amount(symbol[:base_coin_len])
    current_balance_quote = bot.get_coin_amount(symbol[base_coin_len:])
    logging.info('%s\n%s: %2.2f percent change' % (get_readable_timestamp(), state, percentage_price_change))
    verb = 'Bought' if state == 'BUY' else 'Sold'
    logging.info('%s %fcoins for %s' % (verb, coins, current_avg_price))
    logging.info('NEW BALANCE\n%s: %s\n%s: %s' % (symbol[:base_coin_len], current_balance_base, symbol[base_coin_len:], current_balance_quote))


# returns true if bot did sell or buy
def do_next_action(percentage_price_change, bot, calc, symbol, current_price, percentage_balance, decimal_places):
    if (bot.get_state() == 'BUY'):
        if percentage_price_change <= DIP_THRESHOLD or percentage_price_change >= UPWARD_TREND_THRESHOLD:
            current_balance_quote = bot.get_coin_amount(symbol[base_coin_len:])
            print('I buy now')
            coins = calc_trading_coins(calc, current_balance_quote, percentage_balance, current_price, decimal_places)
            print('%f coins for %f' % (coins, current_price))
            bot.send_order_total('MARKET', coins)
            log_trade('BUY', bot, symbol, percentage_price_change, coins, current_price)
            bot.change_state()
            logging.info('STATE: SELL')
            return True
    else:
        if percentage_price_change <= STOP_LOSS_THRESHOLD or percentage_price_change >= PROFIT_THRESHOLD:
            current_balance_quote = bot.get_coin_amount(symbol[base_coin_len:])
            print('I sell now')
            print('The profit would be %f' % (percentage_price_change))
            profit_arr.append(percentage_price_change)
            coins = calc_trading_coins(calc, current_balance_quote, percentage_balance, current_price, decimal_places)
            bot.send_order_total('MARKET', coins)
            log_trade('SELL', bot, symbol, percentage_price_change, coins, current_price)
            bot.change_state()
            logging.info('STATE: BUY')
            profit_arr.append(percentage_price_change)
            return True
    return False

def parse_init_state(symbol):
    text = ''
    with open('logs/trade_history_%s.log' % (symbol), 'r') as file:
        text = file.read()
    states = re.findall('STATE: (BUY|SELL)', text)
    # return state before last state
    if (len(states) > 1):
        return states[len(states) - 2]
    return DEFAULT_STATE

def init_logger(symbol):
    logging.basicConfig(filename='./logs/trade_history_%s.log' % (symbol), level=logging.INFO)
    logging.info(get_readable_timestamp())

# todo split log in loop in methods
def main():
    symbol, percentage, decimal_places = parse_arguments()
    init_logger(symbol)
    init_state = parse_init_state(symbol)
    calc, bot = init_classes(False, init_state, symbol)

    logging.info(bot.get_account_information()['balances'])
    logging.info('Percentage of basecoin balance the bot will trade with: %2.2f' % (percentage))

    print(symbol)
    print('Percentage of balance the bot will trade with: %2.2f' % (percentage))
    print('Decimal places of base coin: %d' % (decimal_places))
    # import balance always quote coin (bnb, btc)
    starting_balance = float(bot.get_coin_amount(symbol[base_coin_len:]))

    bot_loop(calc, bot, symbol, starting_balance, percentage, decimal_places)


try:
    main()
except KeyboardInterrupt:
    logging.info('Profit-Array: %s' % (profit_arr))
except Exception as inst:
    logging.info('Profit-Array: %s' % (profit_arr))
    print(inst)
    print(traceback.format_exc())

# print(bot.get_system_status())
# print(bot.get_coin_information('BNB'))

# print(bot.send_order_total(SYMBOL, 'SELL', 'MARKET', 1))
# print(bot.send_order_quote(SYMBOL, 'BUY', 'MARKET', 75))
# print(bot.get_account_information()['balances'])
# print(bot.get_order_book(SYMBOL))
# print(bot.get_current_average_price(SYMBOL))
# print(bot.get_daily_stats(SYMBOL))

"""
Time: 19h:3min:50sec
Total price change: -0.000001
Percentage price change: -0.05
I buy now
Starting to log


Time: 19h:6min:25sec
Total price change: -0.000001
Percentage price change: -0.03


Time: 19h:8min:58sec
Total price change: 0.000000
Percentage price change: 0.02
I sell now
The profit would be 0.061000 # todo
Starting to log
"""