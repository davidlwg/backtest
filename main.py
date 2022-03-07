import os.path
import sys
import quantstats as qs
import backtrader as bt


# qs.extend_pandas()
# btc = qs.utils.download_returns("BTC-USD")
# print(btc)
# btc.to_csv(r'/Users/david/Projects/backtest/btc-returns.csv')
# qs.stats.sharpe(btc)
# print(btc.sharpe())

#
# qs.plots.snapshot(btc, title="btc performance")
# qs.reports.html(btc, "BTC-USD", output="file")


class TestStrategy(bt.Strategy):
    params = (
        ('exit_bars', 5),
    )

    def log(self, txt, dt=None):
        # logging function
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        self.data_close = self.datas[0].close  # keep reference to the "close" line in the data[0] data series
        self.order = None  # keep track of pending orders
        self.bar_executed = None  # Bar where order was executed
        self.buy_price = None
        self.buy_comm = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Note: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, '
                         f'Price: {order.executed.price}, '
                         f'Cost: {order.executed.value}, '
                         f'Commission: {order.executed.comm}')

                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm

            elif order.issell():
                self.log(f'SELL EXECUTED, '
                         f'Price: {order.executed.price}, '
                         f'Cost: {order.executed.value}, '
                         f'Commission: {order.executed.comm}')

            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'OPERATION PROFIT, GROSS {trade.pnl}, NET {trade.pnlcomm}')

    def next(self):
        self.log(f'Close, {self.data_close[0]}')

        if self.order:
            return

        if not self.position:

            # if closing has decreased 3 days in a row, buy
            if len(self) > 2 and self.data_close[0] < self.data_close[-1]:
                if self.data_close[-1] < self.data_close[-2]:
                    self.log(f'BUY CREATE, {self.data_close[0]}')
                    self.order = self.buy()

        else:
            if self.bar_executed is not None and len(self) >= (self.bar_executed + self.params.exit_bars):
                self.log(f'SELL CREATE, {self.data_close[0]}')
                self.order = self.sell()


if __name__ == '__main__':
    # Create a cerebro entity
    cerebo = bt.Cerebro()

    cerebo.addstrategy(TestStrategy)

    # get data
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    data_path = os.path.join(modpath, 'btc_daily.csv')

    # create Data Feed
    data_feed = bt.feeds.YahooFinanceCSVData(dataname=data_path, reverse=False)

    # add data and set initial cash
    cerebo.adddata(data_feed)
    cerebo.broker.setcash(100000.0)

    # 0.1%
    cerebo.broker.setcommission(commission=0.001)
    cerebo.addsizer(bt.sizers.FixedSize, stake=2)

    print('Starting Portfolio Value: %.2f' % cerebo.broker.get_value())

    cerebo.run()

    print('Final Portfolio Value: %.2f' % cerebo.broker.get_value())
