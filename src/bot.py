import pip._vendor.requests as requests
import time
import hmac
import hashlib

BASE_ENDPOINT = 'https://api.binance.com'

class TradingBot:
    def __init__(self, apiKey, secretKey):
        self.apiKey = apiKey
        self.secretKey = secretKey

        self.header = {
            'X-MBX-APIKEY': self.apiKey 
        }

    def get_account_information(self):
        timestamp = self._get_timestamp_millis()
        payload = {
            'timestamp': timestamp
        }
        self._append_signature(payload)
        print(requests.get(BASE_ENDPOINT + '/api/v3/account', headers=self.header, params=payload).text)

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