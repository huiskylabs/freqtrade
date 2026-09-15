"""Tests for Backpack exchange class."""

import logging
from unittest.mock import MagicMock

from freqtrade.enums import MarginMode, RunMode, TradingMode
from freqtrade.exchange.backpack import Backpack
from freqtrade.exchange.check_exchange import check_exchange
from freqtrade.exchange.exchange_utils import list_available_exchanges
from tests.conftest import get_patched_exchange


def test_backpack_supported_trading_modes():
    assert Backpack._supported_trading_mode_margin_pairs == [
        (TradingMode.SPOT, MarginMode.NONE),
        (TradingMode.FUTURES, MarginMode.CROSS),
    ]


def test_backpack_is_available_for_freqtrade(default_conf):
    default_conf["runmode"] = RunMode.DRY_RUN
    default_conf["exchange"]["name"] = "backpack"

    assert check_exchange(default_conf)
    backpack = [e for e in list_available_exchanges(False) if e["classname"] == "backpack"]

    assert backpack
    assert {"trading_mode": "futures", "margin_mode": "cross"} in backpack[0]["trade_modes"]


def test_backpack_ccxt_config_spot(default_conf_usdt, mocker):
    default_conf_usdt["trading_mode"] = "spot"
    default_conf_usdt["margin_mode"] = ""

    exchange = get_patched_exchange(
        mocker, default_conf_usdt, exchange="backpack", mock_supported_modes=False
    )

    assert exchange._ccxt_config == {"options": {"defaultType": "spot"}}


def test_backpack_ccxt_config_futures(default_conf_usdt, mocker):
    default_conf_usdt["trading_mode"] = "futures"
    default_conf_usdt["margin_mode"] = "cross"

    exchange = get_patched_exchange(
        mocker, default_conf_usdt, exchange="backpack", mock_supported_modes=False
    )

    assert exchange._ccxt_config == {"options": {"defaultType": "swap"}}


def test_backpack_supports_native_stoploss_orders():
    assert Backpack._ft_has["stoploss_on_exchange"] is True
    assert Backpack._ft_has["stoploss_order_types"] == {"market": "market", "limit": "limit"}
    assert Backpack._ft_has["stop_price_param"] == "triggerPrice"
    assert Backpack._ft_has["stop_price_prop"] == "triggerPrice"
    assert Backpack._ft_has["stop_price_type_field"] == "triggerBy"
    assert Backpack._ft_has["stop_price_type_value_mapping"] == {
        "last": "LastPrice",
        "mark": "MarkPrice",
        "index": "IndexPrice",
    }


def test_backpack_parses_numeric_server_time():
    api = MagicMock()
    api.milliseconds.return_value = 123
    assert Backpack._parse_server_time(api, "1789447863293") == 1789447863293
    assert Backpack._parse_server_time(api, {"serverTime": 456}) == 456
    assert Backpack._parse_server_time(api, {}) == 123


def test_backpack_normalizes_position_numbers():
    position = {
        "entryPrice": "100.5",
        "markPrice": "101.0",
        "contracts": "0.01",
        "liquidationPrice": "0",
    }
    fields = ("contracts", "entryPrice", "markPrice", "liquidationPrice")
    Backpack._normalize_position_numbers(position, fields)
    assert position == {
        "entryPrice": 100.5,
        "markPrice": 101.0,
        "contracts": 0.01,
        "liquidationPrice": None,
    }


def test_backpack_dry_run_liquidation_price_returns_none(default_conf_usdt, mocker, caplog):
    default_conf_usdt["trading_mode"] = "futures"
    default_conf_usdt["margin_mode"] = "cross"
    exchange = get_patched_exchange(
        mocker, default_conf_usdt, exchange="backpack", mock_supported_modes=False
    )

    with caplog.at_level(logging.WARNING):
        assert (
            exchange.dry_run_liquidation_price(
                pair="BTC/USDC:USDC",
                open_rate=100_000.0,
                is_short=False,
                amount=0.01,
                stake_amount=100.0,
                leverage=2.0,
                wallet_balance=1_000.0,
                open_trades=[],
            )
            is None
        )

    assert "Backpack dry-run liquidation price cannot be calculated locally" in caplog.text
