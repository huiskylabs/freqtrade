from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy
from technical import qtpylib
from risk_sizing import RiskSizingMixin

class MACDTrendStrategy(RiskSizingMixin, IStrategy):
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
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        return self._fill_swings(dataframe)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[qtpylib.crossed_above(dataframe["macdhist"], 0) & (dataframe["close"] > dataframe["ema50"]) & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[qtpylib.crossed_below(dataframe["macdhist"], 0) & (dataframe["close"] < dataframe["ema50"]) & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
