from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy
from risk_sizing import RiskSizingMixin

class EMARibbonStrategy(RiskSizingMixin, IStrategy):
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

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["ema8"] = ta.EMA(dataframe, timeperiod=8)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema55"] = ta.EMA(dataframe, timeperiod=55)
        return self._fill_swings(dataframe)

    def _entry_stop_price(self, last, side, rate):
        e55 = float(last.get("ema55", rate))
        if side == "long":
            return e55 if e55 < rate else rate * 0.99
        return e55 if e55 > rate else rate * 1.01

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        stack_up = (dataframe["ema8"] > dataframe["ema21"]) & (dataframe["ema21"] > dataframe["ema55"])
        stack_dn = (dataframe["ema8"] < dataframe["ema21"]) & (dataframe["ema21"] < dataframe["ema55"])
        pull_long = (dataframe["low"] <= dataframe["ema21"] * 1.005) & (dataframe["close"] >= dataframe["ema21"])
        pull_short = (dataframe["high"] >= dataframe["ema21"] * 0.995) & (dataframe["close"] <= dataframe["ema21"])
        dataframe.loc[stack_up & pull_long & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[stack_dn & pull_short & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
