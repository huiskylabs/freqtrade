from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative
from risk_sizing import RiskSizingMixin

class DonchianBreakoutStrategy(RiskSizingMixin, IStrategy):
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "2h"
    startup_candle_count = 80
    process_only_new_candles = True
    minimal_roi = {"0": 100}
    stoploss = -0.99
    use_custom_stoploss = True
    trailing_stop = False
    use_exit_signal = False
    use_fixed_2r = True

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["bias_long"] = dataframe["close"] > dataframe["ema50"]
        dataframe["bias_short"] = dataframe["close"] < dataframe["ema50"]
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["don_high"] = dataframe["high"].rolling(20).max()
        dataframe["don_low"] = dataframe["low"].rolling(20).min()
        dataframe["stop_long"] = dataframe["low"].rolling(10).min()
        dataframe["stop_short"] = dataframe["high"].rolling(10).max()
        return self._fill_swings(dataframe)

    def _entry_stop_price(self, last, side, rate):
        if side == "long":
            s = float(last.get("stop_long", rate * 0.99))
            return s if s < rate else rate * 0.99
        s = float(last.get("stop_short", rate * 1.01))
        return s if s > rate else rate * 1.01

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["close"] > dataframe["don_high"].shift(1)) & dataframe["bias_long_4h"].fillna(False) & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[(dataframe["close"] < dataframe["don_low"].shift(1)) & dataframe["bias_short_4h"].fillna(False) & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
