from pandas import DataFrame
import numpy as np
import talib.abstract as ta
from freqtrade.strategy import IStrategy
from risk_sizing import RiskSizingMixin

class SupertrendStrategy(RiskSizingMixin, IStrategy):
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
    st_period = 10
    st_mult = 3.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.st_period)
        hl2 = (dataframe["high"] + dataframe["low"]) / 2
        upper = hl2 + self.st_mult * dataframe["atr"]
        lower = hl2 - self.st_mult * dataframe["atr"]
        st = np.zeros(len(dataframe))
        dir_ = np.ones(len(dataframe))
        for i in range(1, len(dataframe)):
            if dataframe["close"].iloc[i] > upper.iloc[i - 1]:
                dir_[i] = 1
            elif dataframe["close"].iloc[i] < lower.iloc[i - 1]:
                dir_[i] = -1
            else:
                dir_[i] = dir_[i - 1]
                if dir_[i] == 1 and lower.iloc[i] < lower.iloc[i - 1]:
                    lower.iloc[i] = lower.iloc[i - 1]
                if dir_[i] == -1 and upper.iloc[i] > upper.iloc[i - 1]:
                    upper.iloc[i] = upper.iloc[i - 1]
            st[i] = lower.iloc[i] if dir_[i] == 1 else upper.iloc[i]
        dataframe["st_dir"] = dir_
        dataframe["st_line"] = st
        return self._fill_swings(dataframe)

    def _entry_stop_price(self, last, side, rate):
        st = float(last.get("st_line", np.nan))
        if not np.isfinite(st):
            return rate * (0.99 if side == "long" else 1.01)
        if side == "long" and st >= rate:
            return rate * 0.99
        if side == "short" and st <= rate:
            return rate * 1.01
        return st

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        flip_up = (dataframe["st_dir"] == 1) & (dataframe["st_dir"].shift(1) == -1)
        flip_dn = (dataframe["st_dir"] == -1) & (dataframe["st_dir"].shift(1) == 1)
        dataframe.loc[flip_up & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[flip_dn & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
