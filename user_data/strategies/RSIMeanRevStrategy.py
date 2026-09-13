from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative
from risk_sizing import RiskSizingMixin

class RSIMeanRevStrategy(RiskSizingMixin, IStrategy):
    """Fade RSI extremes against 4h EMA20 (range fade). TP at RSI mid ~50."""
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "2h"
    startup_candle_count = 80
    process_only_new_candles = True
    minimal_roi = {"0": 100}
    stoploss = -0.99
    use_custom_stoploss = True
    trailing_stop = False
    use_exit_signal = True
    use_fixed_2r = False  # TP via RSI mid exit

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        # fade: long only when 4h below ema (oversold in down/range), short when above
        dataframe["fade_long_ok"] = dataframe["close"] < dataframe["ema20"]
        dataframe["fade_short_ok"] = dataframe["close"] > dataframe["ema20"]
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return self._fill_swings(dataframe)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] < 30) & dataframe["fade_long_ok_4h"].fillna(False) & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[(dataframe["rsi"] > 70) & dataframe["fade_short_ok_4h"].fillna(False) & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi"] >= 50, "exit_long"] = 1
        dataframe.loc[dataframe["rsi"] <= 50, "exit_short"] = 1
        return dataframe
