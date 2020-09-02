import time
import hmac
import hashlib
import requests

class TradingBot:
    def __init__(self, apiKey, secretKey, baseEndpoint, initState, symbol):
        self.apiKey = apiKey
        self.secretKey = secretKey
        self.baseEndpoint = baseEndpoint
        self.state = initState
        self.symbol = symbol

        self.header = {
            'X-MBX-APIKEY': self.apiKey 
        }

    def get_account_information(self):
        timestamp = self._get_timestamp_millis()
        payload = {
            'timestamp': timestamp
        }
        self._append_signature(payload)
        response = requests.get(self.baseEndpoint + '/api/v3/account', headers=self.header, params=payload)
        response = self._handle_response(response)
        # some hacky stuff
        my_coins = []
        for coin in response['balances']:
            if int(float(coin['free'])) != 0:
                my_coins.append(coin)
        response['balances'] = my_coins
        return response

    def get_system_status(self):
        return requests.get(self.baseEndpoint + '/wapi/v3/systemStatus.html', headers=self.header).text

    def get_global_coin_information(self, coin_name):
        timestamp = self._get_timestamp_millis()
        payload = {
            'timestamp': timestamp
        }
        self._append_signature(payload)
        response = requests.get(self.baseEndpoint + '/sapi/v1/capital/config/getall', headers=self.header, params=payload)
        response = self._handle_response(response)
        return [coin for coin in response if coin.get('coin') == coin_name]

    def get_coin_amount(self, coin_name):
        timestamp = self._get_timestamp_millis()
        payload = {
            'timestamp': timestamp
        }
        self._append_signature(payload)
        response = requests.get(self.baseEndpoint + '/api/v3/account', headers=self.header, params=payload)
        response = self._handle_response(response)
        return [coin['free'] for coin in response['balances'] if coin.get('asset') == coin_name][0]

    def get_state(self):
        return self.state

    def change_state(self):
        self.state = 'SELL' if self.state == 'BUY' else 'BUY'

    def send_order_total(self, type, quantity):
        """
        Parameters
        ----------
        type : str
               e.g. MARKET
        quantity : float
               total sum of coins to trade

        Returns
        -------
        list of object
            Server response on order request
        """
        timestamp = self._get_timestamp_millis()
        payload = {
            'symbol': self.symbol,
            'side': self.state,
            'type': type,
            'quantity': quantity,
            'timestamp': timestamp
        }
        self._append_signature(payload)
        response = requests.post(self.baseEndpoint + '/api/v3/order', headers=self.header, params=payload)
        return self._handle_response(response)

    def send_order_quote(self, type, quoteOrderQty):
        timestamp = self._get_timestamp_millis()
        payload = {
            'symbol': self.symbol,
            'side': self.state,
            'type': type,
            'quoteOrderQty': quoteOrderQty,
            'timestamp': timestamp
        }
        self._append_signature(payload)
        response = requests.post(self.baseEndpoint + '/api/v3/order', headers=self.header, params=payload)
        return self._handle_response(response)
    
    def get_order_book(self):
        payload = {
            'symbol': self.symbol
        }
        response = requests.get(self.baseEndpoint + '/api/v3/depth', headers=self.header, params=payload)
        return self._handle_response(response)

    def get_current_average_price(self):
        payload = {
            'symbol': self.symbol
        }
        response = requests.get(self.baseEndpoint + '/api/v3/avgPrice', params=payload)
        return self._handle_response(response)['price']

    # returns bids and asks from order book
    def get_current_order_book_price(self):
        payload = {
            'symbol': self.symbol
        }
        response = requests.get(self.baseEndpoint + '/api/v3/ticker/bookTicker', params=payload)
        return self._handle_response(response)

    # returns price of current symbol if no other symbol is passed else returns price of other symbol
    def get_symbol_price(self, *args):
        symbol = args[0] if args[0] else self.symbol
        payload = {
            'symbol': symbol
        }
        response = requests.get(self.baseEndpoint + '/api/v3/ticker/price', params=payload)
        return self._handle_response(response)['price']

    def get_daily_stats(self):
        payload = {
            'symbol': self.symbol
        }
        response = requests.get(self.baseEndpoint + '/api/v3/ticker/24hr', params=payload)
        return self._handle_response(response)

    def _handle_response(self, response):
        if response.status_code >= 300 or response.status_code < 200:
            raise Exception(response.text)
        else:
            return response.json()

    def _append_signature(self, payload):
        payload.update({'signature': self._generate_signature(payload)})

    def _generate_signature(self, payload):
        # generate message
        message = ''
        for k in payload:
            message += '{}={}&'.format(k, str(payload.get(k)))
        # remove final '&'
        message = message[:-1]

        # generate signature
        return hmac.new(bytes(self.secretKey , 'latin-1'), msg = bytes(message , 'latin-1'), digestmod = hashlib.sha256).hexdigest()

    def _get_timestamp_millis(self):
        return int(round(time.time() * 1000))