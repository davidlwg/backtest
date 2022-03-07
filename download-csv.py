import yfinance as yf

btc = yf.Ticker("BTC-USD")

# print(btc.info)
#
# print(btc.history(period="max"))

data = yf.download("BTC-USD", group_by="ticker")
print(data)
print(type(data))

data.to_csv(r'/Users/david/Projects/backtest/btc_data.csv')
