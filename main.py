import os.path
import sys
import backtrader as bt

class TestStrategy(bt.Strategy):
    params = (
        ('ma_period', 33),
        ('print_log', True),
        ('sma', True),
        ('ema', False),
        ('macd', False)
    )

    def log(self, txt, dt=None, do_print=False):
        # logging function
        if self.params.print_log or do_print:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        self.data_close = self.datas[0].close  # keep reference to the "close" line in the data[0] data series
        self.order = None  # keep track of pending orders
        self.bar_executed = None  # Bar where order was executed
        self.buy_price = None
        self.buy_comm = None

        # SMA indicator
        if self.params.sma:
            self.indicator = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.ma_period)
        elif self.params.ema:
            self.indicator = bt.indicators.ExponentialMovingAverage(self.datas[0], period=self.params.ma_period)
        elif self.params.macd:
            self.macd = bt.indicators.MACD(self.datas[0], period_me1=12, period_me2=26, period_signal=9)
            self.mcross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # # indicators for plotting
        # bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        # bt.indicators.WeightedMovingAverage(self.datas[0], period=25, subplot=True)
        # bt.indicators.Stochastic(self.datas[0])
        # bt.indicators.MACDHisto(self.datas[0])
        # rsi = bt.indicators.RSI(self.datas[0])
        # bt.indicators.SmoothedMovingAverage(rsi, period=10)
        # bt.indicators.ATR(self.datas[0], plot=False)

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

    def __moving_average(self):
        if not self.position:
            if self.data_close[0] > self.indicator[0]:
                self.log(f'BUY CREATE, {self.data_close[0]}')
                self.order = self.buy()

        else:
            if self.bar_executed is not None and self.data_close[0] < self.indicator[0]:
                self.log(f'SELL CREATE, {self.data_close[0]}')
                self.order = self.sell()

    def __macd(self):
        if not self.position:
            if self.mcross > 0:
                self.log(f'BUY CREATE, {self.data_close[0]}')
                self.order = self.buy()

        else:
            if self.bar_executed is not None and self.mcross < 0:
                self.log(f'SELL CREATE, {self.data_close[0]}')
                self.order = self.sell()

    def next(self):
        self.log(f'Close, {self.data_close[0]}')

        if self.order:
            return

        if self.params.sma or self.params.ema:
            self.__moving_average()

        if self.params.macd:
            self.__macd()

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f'
                 % (self.params.ma_period, self.broker.getvalue()), do_print=True)


if __name__ == '__main__':
    # Create a cerebro entity
    cerebo = bt.Cerebro()

    # cerebo.optstrategy(TestStrategy, ma_period=range(10, 140))
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

    cerebo.run(maxcpus=1)

    print('Final Portfolio Value: %.2f' % cerebo.broker.get_value())

    cerebo.plot()
