from bot import TradingBot

API_KEY = 'kcaIZBT8GD5fjYJAejac1cZhQOlYIYcqo06c1jVLS2HdaU6i2xdW0k8JQG3RTTML'
SECRET_KEY = 'AgsacP06Ph7M2HhtoF67HHrH1HLy4jLyEncyEB2Ke4aXIS6qsb4rlnHO6lW4SQgB'

bot = TradingBot(API_KEY, SECRET_KEY)

bot.get_account_information()