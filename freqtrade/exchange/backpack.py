"""Backpack exchange subclass."""

import inspect
import logging
from typing import Any

import ccxt

from freqtrade.enums import MarginMode, PriceType, TradingMode
from freqtrade.exceptions import (
    DDosProtection,
    InvalidOrderException,
    OperationalException,
    RetryableOrderError,
    TemporaryError,
)
from freqtrade.exchange import Exchange
from freqtrade.exchange.common import API_FETCH_ORDER_RETRY_COUNT, retrier
from freqtrade.exchange.exchange_types import CcxtOrder, FtHas
from freqtrade.misc import deep_merge_dicts


logger = logging.getLogger(__name__)


class Backpack(Exchange):
    """Backpack exchange class.

    Backpack futures are cross-margined at subaccount level. Leverage and risk segregation are
    configured on Backpack's side, not per position through CCXT.
    """

    _ft_has: FtHas = {
        "order_time_in_force": ["GTC", "FOK", "IOC", "PO"],
        # Backpack conditional orders use a market/limit order plus triggerPrice.
        # Freqtrade's stoploss-on-exchange path adds reduceOnly for futures.
        "stoploss_on_exchange": True,
        "stoploss_order_types": {"market": "market", "limit": "limit"},
        "stop_price_param": "triggerPrice",
        "stop_price_prop": "triggerPrice",
        "stop_price_type_field": "triggerBy",
        "stop_price_type_value_mapping": {
            PriceType.LAST: "LastPrice",
            PriceType.MARK: "MarkPrice",
            PriceType.INDEX: "IndexPrice",
        },
    }
    _ft_has_futures: FtHas = {
        # Backpack only supports cross margin for futures. CCXT exposes futures as swaps.
        "ccxt_futures_name": "swap",
        # CCXT has no fetchLeverageTiers for Backpack yet; mirror Hyperliquid for backtesting.
        "uses_leverage_tiers": False,
        "mark_ohlcv_price": "futures",
    }

    _supported_trading_mode_margin_pairs: list[tuple[TradingMode, MarginMode]] = [
        (TradingMode.SPOT, MarginMode.NONE),
        (TradingMode.FUTURES, MarginMode.CROSS),
    ]

    @property
    def _ccxt_config(self) -> dict[str, Any]:
        # Backpack supports spot and perpetual futures. Make the intended market type explicit
        # for both sync and async CCXT clients.
        config = {}
        if self.trading_mode == TradingMode.SPOT:
            config.update({"options": {"defaultType": "spot"}})
        elif self.trading_mode == TradingMode.FUTURES:
            config.update({"options": {"defaultType": self._ft_has["ccxt_futures_name"]}})
        return deep_merge_dicts(config, super()._ccxt_config)

    def _init_ccxt(
        self, exchange_config: dict[str, Any], sync: bool, ccxt_kwargs: dict[str, Any]
    ) -> ccxt.Exchange:
        api = super()._init_ccxt(exchange_config, sync, ccxt_kwargs)
        self._normalize_ccxt_timeframes(api)
        self._bound_ohlcv_until(api)
        self._normalize_server_time(api)
        return api

    @staticmethod
    def _normalize_server_time(api: ccxt.Exchange) -> None:
        """Parse Backpack's numeric /api/v1/time response correctly.

        CCXT's generic safe_integer parser treats the raw numeric response as an
        indexable value and can return ``1`` instead of the millisecond timestamp.
        That produces a massive false clock-difference warning and can invalidate
        authenticated requests. Keep the patch local to Backpack.
        """
        def parse(response):
            if isinstance(response, (int, float, str)):
                try:
                    return int(response)
                except (TypeError, ValueError):
                    pass
            if isinstance(response, dict):
                for key in ("timestamp", "time", "serverTime"):
                    if key in response:
                        try:
                            return int(response[key])
                        except (TypeError, ValueError):
                            pass
            return api.milliseconds()

        if inspect.iscoroutinefunction(api.fetch_time):
            async def fetch_time(params=None):
                response = await api.publicGetApiV1Time(params or {})
                return parse(response)
        else:
            def fetch_time(params=None):
                response = api.publicGetApiV1Time(params or {})
                return parse(response)
        api.fetch_time = fetch_time  # type: ignore[method-assign]

    @staticmethod
    def _normalize_ccxt_timeframes(api: ccxt.Exchange) -> None:
        """Alias CCXT Backpack's inverted 15/30 keys to standard 15m/30m names.

        Upstream CCXT currently exposes ``{'15': '15m', '30': '30m'}``, which makes Freqtrade
        reject timeframe ``30m``. Keep the original keys and add the standard aliases so both
        download-data and backtesting can use ``30m`` / ``15m``.
        """
        tfs = dict(getattr(api, "timeframes", None) or {})
        aliases = {"15": "15m", "30": "30m"}
        changed = False
        for bad, good in aliases.items():
            if bad in tfs and good not in tfs:
                tfs[good] = tfs[bad] or good
                changed = True
        if changed:
            api.timeframes = tfs

    @staticmethod
    def _bound_ohlcv_until(api: ccxt.Exchange) -> None:
        """CCXT Backpack omits endTime when since is set, so the API defaults to now.

        Backpack then rejects the request if startTime..now is too long. Bound ``until`` to
        ``since + limit * timeframe`` so pagination windows stay valid.
        """
        orig = api.fetch_ohlcv

        def _with_until(since, timeframe, limit, params):
            params = dict(params or {})
            if since is not None and params.get("until") is None:
                duration = api.parse_timeframe(timeframe)  # seconds
                lim = limit or 500
                params["until"] = int(since) + int(lim) * int(duration) * 1000
            return params

        if inspect.iscoroutinefunction(orig):

            async def fetch_ohlcv(symbol, timeframe="1m", since=None, limit=None, params=None):
                params = _with_until(since, timeframe, limit, params)
                return await orig(symbol, timeframe, since, limit, params)

        else:

            def fetch_ohlcv(symbol, timeframe="1m", since=None, limit=None, params=None):
                params = _with_until(since, timeframe, limit, params)
                return orig(symbol, timeframe, since, limit, params)

        api.fetch_ohlcv = fetch_ohlcv  # type: ignore[method-assign]

    @retrier(retries=API_FETCH_ORDER_RETRY_COUNT)
    def fetch_positions(self, pair: str | None = None, params: dict | None = None):
        """Fetch Backpack positions with numeric CCXT fields normalized.

        Backpack can return numeric position fields as strings. Freqtrade's
        post-fill liquidation calculation performs arithmetic on these values.
        A zero liquidation price means Backpack did not provide one for the
        cross-margin account and must remain unavailable rather than synthetic.
        """
        positions = super().fetch_positions(pair, params)
        numeric_fields = (
            "contracts", "contractSize", "entryPrice", "markPrice", "notional",
            "leverage", "collateral", "initialMargin", "maintenanceMargin",
            "unrealizedPnl", "realizedPnl", "liquidationPrice",
        )
        for position in positions:
            for field in numeric_fields:
                value = position.get(field)
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        continue
                if field == "liquidationPrice" and value is not None and value <= 0:
                    value = None
                position[field] = value
        return positions

    @retrier(retries=API_FETCH_ORDER_RETRY_COUNT)
    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """Fetch an order.

        CCXT Backpack does not expose ``fetchOrder``. Open orders can be fetched directly with
        ``fetchOpenOrder``; closed orders are found through ``fetchOrders``.
        """
        if self._config["dry_run"]:
            return self.fetch_dry_run_order(order_id)
        params = params or {}
        try:
            order = self._api.fetch_open_order(order_id, pair, params=params)
            self._log_exchange_response("fetch_open_order", order)
            return self._order_contracts_to_amount(order)
        except ccxt.OrderNotFound:
            pass
        except ccxt.ExchangeNotAvailable as e:
            # Backpack returns HTTP 404 / RESOURCE_NOT_FOUND for orders that
            # are no longer open. Continue to fetch order history instead of
            # treating a normal cancellation/expiry as an exchange outage.
            message = str(e)
            if "RESOURCE_NOT_FOUND" in message or "Not Found" in message:
                pass
            else:
                raise TemporaryError(
                    f"Could not get order due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.InvalidOrder as e:
            raise InvalidOrderException(
                f"Tried to get an invalid order (pair: {pair} id: {order_id}). Message: {e}"
            ) from e
        except ccxt.DDoSProtection as e:
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f"Could not get order due to {e.__class__.__name__}. Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            raise OperationalException(e) from e

        try:
            orders = self._api.fetch_orders(pair, None, None, params=params)
            self._log_exchange_response("fetch_orders", orders)
            order = next((order for order in orders if order["id"] == order_id), None)
            if order:
                return self._order_contracts_to_amount(order)
            raise RetryableOrderError(f"Order not found (pair: {pair} id: {order_id}).")
        except ccxt.OrderNotFound as e:
            raise RetryableOrderError(
                f"Order not found (pair: {pair} id: {order_id}). Message: {e}"
            ) from e
        except ccxt.InvalidOrder as e:
            raise InvalidOrderException(
                f"Tried to get an invalid order (pair: {pair} id: {order_id}). Message: {e}"
            ) from e
        except ccxt.DDoSProtection as e:
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f"Could not get order due to {e.__class__.__name__}. Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            raise OperationalException(e) from e

    def dry_run_liquidation_price(
        self,
        pair: str,
        open_rate: float,
        is_short: bool,
        amount: float,
        stake_amount: float,
        leverage: float,
        wallet_balance: float,
        open_trades: list,
    ) -> float | None:
        """Return no synthetic liquidation price for Backpack dry-run/backtesting.

        Backpack's liquidation model is account-level cross margin and depends on subaccount
        collateral, borrow/lend state, open orders, and per-market margin fractions. Without the
        full account risk model exposed as Freqtrade leverage tiers, a local estimate would be
        misleading. Live mode uses CCXT ``fetchPositions`` liquidation prices when Backpack returns
        them.
        """
        logger.warning(
            "Backpack dry-run liquidation price cannot be calculated locally. "
            "Use conservative stoploss settings and validate live/testnet behavior carefully."
        )
        return None


    def get_max_leverage(self, pair: str, stake_amount: float | None) -> float:
        """Backpack has no CCXT leverage tiers; allow up to 20x for futures."""
        if self.trading_mode == TradingMode.SPOT:
            return 1.0
        return 20.0
