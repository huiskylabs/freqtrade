from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy
from risk_sizing import RiskSizingMixin

class BollSqueezeStrategy(RiskSizingMixin, IStrategy):
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "2h"
    startup_candle_count = 120
    process_only_new_candles = True
    minimal_roi = {"0": 100}
    stoploss = -0.99
    use_custom_stoploss = True
    trailing_stop = False
    use_exit_signal = False
    use_fixed_2r = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        boll = ta.BBANDS(dataframe, timeperiod=20)
        dataframe["bb_upper"] = boll["upperband"]
        dataframe["bb_mid"] = boll["middleband"]
        dataframe["bb_lower"] = boll["lowerband"]
        width = (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe["bb_mid"]
        dataframe["bb_width"] = width
        dataframe["bb_width_pct"] = width.rolling(100).apply(lambda s: 100.0 * float(s.rank(pct=True).iloc[-1]), raw=False)
        return self._fill_swings(dataframe)

    def _entry_stop_price(self, last, side, rate):
        mid = float(last.get("bb_mid", rate))
        if side == "long":
            return mid if mid < rate else rate * 0.99
        return mid if mid > rate else rate * 1.01

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        squeeze = dataframe["bb_width_pct"] < 20
        dataframe.loc[squeeze & (dataframe["close"] > dataframe["bb_upper"]) & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[squeeze & (dataframe["close"] < dataframe["bb_lower"]) & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
