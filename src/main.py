import os.path
import sys
import backtrader as bt
import backtrader.analyzers as btanalyze
import quantstats as qs

class TestStrategy(bt.Strategy):
    params = (
        ('ma_period', 33),
        ('print_log', False),
        ('sma', False),
        ('ema', False),
        ('macd', True),
        ('risk_percentage', 0.03)
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

            self.atr = bt.indicators.ATR(self.datas[0], period=14)

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
        close = self.data_close[0]

        if not self.position:
            if close > self.indicator[0]:
                self.log(f'BUY CREATE, {close}')
                self.order = self.buy()
        else:
            if self.bar_executed is not None and close < self.indicator[0]:
                self.log(f'SELL CREATE, {close}')
                self.order = self.sell()

    # https://www.backtrader.com/blog/posts/2016-07-30-macd-settings/macd-settings/#and-the-code-itself
    def __macd(self):
        close = self.data_close[0]

        if not self.position:
            if self.mcross > 0:
                stop_loss_dist = self.atr[0] * 3
                self.stop_loss = close - stop_loss_dist

                position_size = (self.broker.getvalue() * self.params.risk_percentage)
                self.position_qty = position_size / stop_loss_dist
                print(self.position_qty)

                self.log(f'BUY CREATE, {close}')
                self.order = self.buy(size=self.position_qty)

        else:
            stop_loss = self.stop_loss

            if self.bar_executed is not None:
                if close < stop_loss:
                    self.log(f'SELL CREATE, {close}')
                    self.order = self.sell(size=self.position_qty)
                    self.position_qty = 0
                else:
                    new_stop_loss_dist = self.atr[0] * 3
                    self.stop_loss = max(self.stop_loss, close - new_stop_loss_dist)

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


def simple():
    cerebo.run(maxcpus=1)

    print('Final Portfolio Value: %.2f' % cerebo.broker.get_value())


def full():
    # export to quantstats
    # https://algotrading101.com/learn/backtrader-for-backtesting/
    cerebo.addanalyzer(btanalyze.PyFolio, _name="Quantstats")

    results = cerebo.run(maxcpus=1)
    result = results[0]

    portfolio_stats = result.analyzers.getbyname("Quantstats")
    return_stats, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
    return_stats.index = return_stats.index.tz_convert(None)

    print('Final Portfolio Value: %.2f' % cerebo.broker.get_value())

    qs.reports.html(return_stats, "BTC-USD", output="file")

    cerebo.plot()


if __name__ == '__main__':
    # Create a cerebro entity
    cerebo = bt.Cerebro()

    # cerebo.optstrategy(TestStrategy, ma_period=range(10, 140))
    cerebo.addstrategy(TestStrategy)

    # get data
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    data_path = os.path.join(modpath, '../data/btc_OHLC.csv')
    print(data_path)

    # create Data Feed
    data_feed = bt.feeds.YahooFinanceCSVData(dataname=data_path, reverse=False)

    # add data and set initial cash
    cerebo.adddata(data_feed)
    cerebo.broker.setcash(100000.0)

    # 0.1%
    cerebo.broker.setcommission(commission=0.001)
    cerebo.addsizer(bt.sizers.FixedSize, stake=20)

    print('Starting Portfolio Value: %.2f' % cerebo.broker.get_value())

    # simple()
    full()
