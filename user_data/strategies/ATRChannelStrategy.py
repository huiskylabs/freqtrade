from pandas import DataFrame
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, stoploss_from_absolute
from risk_sizing import RiskSizingMixin

class ATRChannelStrategy(RiskSizingMixin, IStrategy):
    """Break ATR channel; trail ATR*2 (no fixed 2R)."""
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
    use_fixed_2r = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        mid = dataframe["close"].rolling(20).mean()
        dataframe["chan_mid"] = mid
        dataframe["chan_upper"] = mid + dataframe["atr"]
        dataframe["chan_lower"] = mid - dataframe["atr"]
        return self._fill_swings(dataframe)

    def _entry_stop_price(self, last, side, rate):
        # initial stop mid-channel
        mid = float(last.get("chan_mid", rate))
        if side == "long":
            return mid if mid < rate else rate * 0.99
        return mid if mid > rate else rate * 1.01

    def custom_stoploss(self, pair, trade: Trade, current_time, current_rate, current_profit, after_fill, **kwargs):
        # trail ATR*2 from extreme
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return None
        last = df.iloc[-1]
        atr = float(last.get("atr", current_rate * 0.01))
        if trade.is_short:
            stop = current_rate + 2.0 * atr
        else:
            stop = current_rate - 2.0 * atr
        return stoploss_from_absolute(stop, current_rate, is_short=trade.is_short, leverage=trade.leverage or 1.0)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["close"] > dataframe["chan_upper"]) & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[(dataframe["close"] < dataframe["chan_lower"]) & (dataframe["volume"] > 0), "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
