import yfinance as yf
import quantstats as qs

# btc = yf.Ticker("BTC-USD")
#
# # print(btc.info)
# #
# # print(btc.history(period="max"))
#
# data = yf.download("BTC-USD", group_by="ticker")
# print(data)
# print(type(data))
#
# data.to_csv(r'/Users/david/Projects/backtest/btc_data.csv')


qs.extend_pandas()
btc = qs.utils.download_returns("BTC-USD")
print(btc)
btc.to_csv(r'/Users/david/Projects/backtest/btc-returns.csv')
# qs.stats.sharpe(btc)
# print(btc.sharpe())

#
# qs.plots.snapshot(btc, title="btc performance")
# qs.reports.html(btc, "BTC-USD", output="file")
