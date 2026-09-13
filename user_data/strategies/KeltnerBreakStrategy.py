from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative
from risk_sizing import RiskSizingMixin

class KeltnerBreakStrategy(RiskSizingMixin, IStrategy):
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
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["bias_long"] = dataframe["close"] > dataframe["ema20"]
        dataframe["bias_short"] = dataframe["close"] < dataframe["ema20"]
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["kc_mid"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["kc_upper"] = dataframe["kc_mid"] + 1.5 * dataframe["atr"]
        dataframe["kc_lower"] = dataframe["kc_mid"] - 1.5 * dataframe["atr"]
        return self._fill_swings(dataframe)

    def _entry_stop_price(self, last, side, rate):
        mid = float(last.get("kc_mid", rate))
        if side == "long":
            return mid if mid < rate else rate * 0.99
        return mid if mid > rate else rate * 1.01

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["close"] > dataframe["kc_upper"]) & dataframe["bias_long_4h"].fillna(False) & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[(dataframe["close"] < dataframe["kc_lower"]) & dataframe["bias_short_4h"].fillna(False) & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
