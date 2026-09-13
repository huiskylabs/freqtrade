"""Backpack exchange subclass."""

import logging
from typing import Any

import ccxt

from freqtrade.enums import MarginMode, TradingMode
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
