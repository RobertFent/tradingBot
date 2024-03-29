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
        bot = TradingBot(API_KEY_TEST, SECRET_KEY_TEST, BASE_ENDPOINT_TEST,
                         init_state, symbol)
    else:
        bot = TradingBot(API_KEY, SECRET_KEY, BASE_ENDPOINT, init_state,
                         symbol)
    return calc, bot


def parse_arguments():
    parser = argparse.ArgumentParser('My Trading Bot')
    parser.add_argument('symbol',
                        type=str,
                        default=DEFAULT_SYMBOL,
                        help='Symbol the bot shall trade',
                        nargs='?')
    parser.add_argument('percentage',
                        type=float,
                        default=DEFAULT_PERCENTAGE,
                        help='Amount of current balance the bot shall trade',
                        nargs='?')
    parser.add_argument(
        'decimal_places',
        type=int,
        default=DEFAULT_DECIMAL_PLACES,
        help='Number of decimal places behind coin for trading',
        nargs='?')
    parser.add_argument('init_state',
                        type=str,
                        default=None,
                        help='Initial state of bot (BUY or SELL)',
                        nargs='?')
    args = parser.parse_args()
    symbol = args.symbol
    percentage = round(args.percentage, 2)
    decimal_places = int(args.decimal_places)
    init_state = args.init_state
    return symbol, percentage, decimal_places, init_state


def get_readable_timestamp():
    return '%sh:%smin:%ssec' % (time.localtime().tm_hour,
                                time.localtime().tm_min,
                                time.localtime().tm_sec)


def bot_loop(calc, bot, symbol, starting_balance, percentage_balance,
             decimal_places):
    default_price = float(bot.get_symbol_price())
    i = 0
    while True:
        current_price = float(bot.get_symbol_price())
        total_price_change = calc.get_total_change(current_price,
                                                   default_price)
        percentage_price_change = round(
            calc.get_percentage_change(current_price, default_price), 3)

        if i % 5 == 0:
            print('\n\nTime: %s' % (get_readable_timestamp()))
            print('Default price: %f' % (default_price))
            print('Current price: %f' % (current_price))
            print('Total price change: %f' % (total_price_change))
            print('Percentage price change: %2.2f' % (percentage_price_change))

        if should_exit(bot, symbol, starting_balance):
            raise Exception('Time to go now')

        if do_next_action(percentage_price_change, bot, calc, symbol,
                          current_price, percentage_balance, decimal_places):
            print('Bought or sold')
            print('Current default price %f' % (default_price))
            default_price = current_price
            print('Setting new default price to %f' % (default_price))
        time.sleep(30)
        i += 1


def get_total_balance(bot, symbol):
    # get current balance of quote coin
    current_balance = float(bot.get_coin_amount(symbol[len(BASE_COIN):]))
    # also add every other coin from this pair to current balance to make bot run simultanioulsy
    balances = bot.get_account_information()['balances']
    # calc value of each base coin to quote coin value
    for balance in balances:
        symbol_name = balance['asset'] + symbol[len(BASE_COIN):]
        symbol_price = bot.get_symbol_price(symbol_name)
        estimated_quote_value = float(balance['free']) * float(symbol_price)
        current_balance += estimated_quote_value
    return current_balance


# returns true if current balance is twice as great or half starting balance
# todo magic numbers
def should_exit(bot, symbol, starting_balance):
    # get current balance of quote and base coin
    current_balance = get_total_balance(bot, symbol)
    if current_balance < float(starting_balance) / 3 or current_balance > float(
            starting_balance) * 2:
        print('Exit!')
        print('Current balance: %f' % (current_balance))
        print('Starting balance: %f' % (starting_balance))
        return True
    return False


# todo? round needed?
def calc_trading_coins(calc, current_balance, percentage_balance,
                       current_price, decimal_places):
    base_coins = calc.get_amount_by_percentage(percentage_balance,
                                               current_balance)
    trading_coins = round(base_coins / current_price, decimal_places)
    if (decimal_places < 1): return int(trading_coins)
    return trading_coins


def log_trade(state, bot, symbol, percentage_price_change, coins,
              current_avg_price):
    current_balance_base = bot.get_coin_amount(symbol[:len(BASE_COIN)])
    current_balance_quote = bot.get_coin_amount(symbol[len(BASE_COIN):])
    logging.info('%s\n%s: %2.2f percent change' %
                 (get_readable_timestamp(), state, percentage_price_change))
    verb = 'Bought' if state == 'BUY' else 'Sold'
    logging.info('%s %fcoins for %s' % (verb, coins, current_avg_price))
    logging.info('NEW BALANCE\n%s: %s\n%s: %s' %
                 (symbol[:len(BASE_COIN)], current_balance_base,
                  symbol[len(BASE_COIN):], current_balance_quote))


# returns true if bot did sell or buy
def do_next_action(percentage_price_change, bot, calc, symbol, current_price,
                   percentage_balance, decimal_places):
    if (bot.get_state() == 'BUY'):
        if percentage_price_change <= DIP_THRESHOLD or percentage_price_change >= UPWARD_TREND_THRESHOLD:
            current_balance_quote = bot.get_coin_amount(
                symbol[len(BASE_COIN):])
            print('I buy now')
            # buy coins depending on wanted percentage of total balance
            coins = calc_trading_coins(calc, current_balance_quote,
                                       percentage_balance, current_price,
                                       decimal_places)
            print('%f coins for %f' % (coins, current_price))
            bot.send_order_total('MARKET', coins)
            log_trade('BUY', bot, symbol, percentage_price_change, coins,
                      current_price)
            bot.change_state()
            logging.info('STATE: SELL')
            return True
    else:
        if percentage_price_change <= STOP_LOSS_THRESHOLD or percentage_price_change >= PROFIT_THRESHOLD:
            current_balance_quote = bot.get_coin_amount(
                symbol[len(BASE_COIN):])
            print('I sell now')
            print('The profit would be %f' % (percentage_price_change))
            profit_arr.append(percentage_price_change)
            # sell all base coins (ADA, FET, NEO etc.)
            coins = round(float(bot.get_coin_amount(symbol[:len(BASE_COIN)])),
                          decimal_places)
            #coins = calc_trading_coins(calc, current_balance_quote,
            #                           percentage_balance, current_price,
            #                           decimal_places)
            bot.send_order_total('MARKET', coins)
            log_trade('SELL', bot, symbol, percentage_price_change, coins,
                      current_price)
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
    # return last state
    if (len(states) > 0):
        return states[len(states) - 1]
    return DEFAULT_STATE


def init_logger(symbol):
    logging.basicConfig(filename='./logs/trade_history_%s.log' % (symbol),
                        level=logging.INFO)
    logging.info(get_readable_timestamp())


# todo split log in loop in methods
def main():
    symbol, percentage, decimal_places, init_state = parse_arguments()
    init_logger(symbol)
    if (init_state == None):
        init_state = parse_init_state(symbol)
    calc, bot = init_classes(False, init_state, symbol)

    starting_balance_quote = float(bot.get_coin_amount(symbol[len(BASE_COIN):]))
    starting_balance_base = float(bot.get_coin_amount(symbol[:len(BASE_COIN)]))
    # get current balance of quote and base coin
    starting_balance_total = get_total_balance(bot, symbol)
    logging.info(bot.get_account_information()['balances'])
    logging.info(
        'Percentage of basecoin balance the bot will trade with: %2.2f' %
        (percentage))

    print(symbol)
    print('Init state: %s' % (init_state))
    print('Starting balance quote (%s): %f' %
          (symbol[len(BASE_COIN):], starting_balance_quote))
    print('Starting balance base (%s): %f' %
          (symbol[:len(BASE_COIN)], starting_balance_base))
    print('Percentage of balance the bot will trade with: %2.2f' %
          (percentage))
    print('Decimal places of base coin: %d' % (decimal_places))

    bot_loop(calc, bot, symbol, starting_balance_total, percentage, decimal_places)


try:
    main()
except KeyboardInterrupt:
    logging.info('Profit-Array: %s' % (profit_arr))
except Exception as inst:
    logging.info('Profit-Array: %s' % (profit_arr))
    logging.info('Error: %s' % (traceback.format_exc()))
    print(inst)
    print(traceback.format_exc())

# print(bot.get_system_status())
# print(bot.get_coin_information('BNB'))

# print(bot.get_order_book(SYMBOL))
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
'''
# todo sell calc?
❯ python3 src/program.py 'FETBNB'
FETBNB
Percentage of balance the bot will trade with: 0.25
Decimal places of base coin: 0


Time: 12h:57min:46sec
Total price change: 0.000000
Percentage price change: 0.00


Time: 13h:0min:20sec
Total price change: 0.000003
Percentage price change: 0.07


Time: 13h:2min:53sec
Total price change: 0.000016
Percentage price change: 0.35


Time: 13h:5min:27sec
Total price change: 0.000036
Percentage price change: 0.79


Time: 13h:8min:1sec
Total price change: 0.000017
Percentage price change: 0.38


Time: 13h:10min:35sec
Total price change: -0.000013
Percentage price change: -0.29


Time: 13h:13min:8sec
Total price change: -0.000022
Percentage price change: -0.48


Time: 13h:15min:41sec
Total price change: 0.000031
Percentage price change: 0.68


Time: 13h:18min:15sec
Total price change: 0.000035
Percentage price change: 0.77


Time: 13h:20min:49sec
Total price change: 0.000040
Percentage price change: 0.88


Time: 13h:23min:22sec
Total price change: 0.000066
Percentage price change: 1.46


Time: 13h:25min:56sec
Total price change: 0.000052
Percentage price change: 1.15


Time: 13h:28min:29sec
Total price change: 0.000047
Percentage price change: 1.04


Time: 13h:31min:3sec
Total price change: 0.000046
Percentage price change: 1.01


Time: 13h:33min:37sec
Total price change: 0.000046
Percentage price change: 1.01


Time: 13h:36min:10sec
Total price change: 0.000076
Percentage price change: 1.68


Time: 13h:38min:43sec
Total price change: 0.000062
Percentage price change: 1.37


Time: 13h:41min:17sec
Total price change: 0.000080
Percentage price change: 1.76


Time: 13h:43min:50sec
Total price change: 0.000085
Percentage price change: 1.88
I buy now
56.000000 coins for 0.004638


Time: 13h:46min:25sec
Total price change: 0.000021
Percentage price change: 0.45


Time: 13h:48min:58sec
Total price change: 0.000076
Percentage price change: 1.64


Time: 13h:51min:32sec
Total price change: 0.000059
Percentage price change: 1.27


Time: 13h:54min:6sec
Total price change: -0.000011
Percentage price change: -0.24


Time: 13h:56min:40sec
Total price change: -0.000030
Percentage price change: -0.65


Time: 13h:59min:13sec
Total price change: -0.000054
Percentage price change: -1.16


Time: 14h:1min:47sec
Total price change: -0.000049
Percentage price change: -1.06


Time: 14h:4min:20sec
Total price change: -0.000052
Percentage price change: -1.12


Time: 14h:6min:53sec
Total price change: -0.000062
Percentage price change: -1.34
I sell now
The profit would be -2.091000


Time: 14h:9min:28sec
Total price change: 0.000011
Percentage price change: 0.24


Time: 14h:12min:2sec
Total price change: 0.000062
Percentage price change: 1.36


Time: 14h:14min:35sec
Total price change: 0.000062
Percentage price change: 1.36
I buy now
39.000000 coins for 0.004682


Time: 14h:17min:10sec
Total price change: 0.000007
Percentage price change: 0.15


Time: 14h:19min:43sec
Total price change: 0.000029
Percentage price change: 0.62


Time: 14h:22min:17sec
Total price change: 0.000004
Percentage price change: 0.09


Time: 14h:24min:50sec
Total price change: -0.000006
Percentage price change: -0.13


Time: 14h:27min:24sec
Total price change: 0.000015
Percentage price change: 0.32


Time: 14h:29min:57sec
Total price change: 0.000015
Percentage price change: 0.32


Time: 14h:32min:31sec
Total price change: 0.000006
Percentage price change: 0.13


Time: 14h:35min:5sec
Total price change: -0.000016
Percentage price change: -0.34


Time: 14h:37min:38sec
Total price change: -0.000039
Percentage price change: -0.83


Time: 14h:40min:11sec
Total price change: -0.000033
Percentage price change: -0.70


Time: 14h:42min:45sec
Total price change: -0.000008
Percentage price change: -0.17


Time: 14h:45min:19sec
Total price change: -0.000007
Percentage price change: -0.15


Time: 14h:47min:52sec
Total price change: 0.000002
Percentage price change: 0.04


Time: 14h:50min:25sec
Total price change: -0.000011
Percentage price change: -0.23


Time: 14h:53min:7sec
Total price change: -0.000011
Percentage price change: -0.23


Time: 14h:55min:41sec
Total price change: -0.000013
Percentage price change: -0.28


Time: 14h:58min:15sec
Total price change: -0.000013
Percentage price change: -0.28
I sell now
The profit would be -2.499000


Time: 15h:0min:49sec
Total price change: -0.000008
Percentage price change: -0.17
I buy now
38.000000 coins for 0.004493
Time to go now
Traceback (most recent call last):
  File "src/program.py", line 200, in <module>
    main()
  File "src/program.py", line 196, in main
    bot_loop(calc, bot, symbol, starting_balance, percentage, decimal_places)
  File "src/program.py", line 107, in bot_loop
    raise Exception('Time to go now')
Exception: Time to go now
'''
