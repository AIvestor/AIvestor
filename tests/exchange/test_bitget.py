from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from freqtrade.enums import CandleType
from freqtrade.enums.marginmode import MarginMode
from freqtrade.enums.tradingmode import TradingMode
from freqtrade.exceptions import TemporaryError
from tests.conftest import EXMS, get_mock_coro, get_patched_exchange, log_has


async def test_bitget_fetch_funding_rate(default_conf, mocker):
    default_conf["trading_mode"] = "futures"
    default_conf["margin_mode"] = "isolated"
    api_mock = MagicMock()
    api_mock.fetch_funding_rate_history = get_mock_coro(return_value=[])
    exchange = get_patched_exchange(mocker, default_conf, exchange="bitget", api_mock=api_mock)
    limit = 200
    # Test fetch_funding_rate_history (current data)
    await exchange._fetch_funding_rate_history(
        pair="BTC/USDT:USDT",
        timeframe="4h",
        limit=limit,
    )

    assert api_mock.fetch_funding_rate_history.call_count == 1
    assert api_mock.fetch_funding_rate_history.call_args_list[0][0][0] == "BTC/USDT:USDT"
    kwargs = api_mock.fetch_funding_rate_history.call_args_list[0][1]
    assert kwargs["since"] is None

    api_mock.fetch_funding_rate_history.reset_mock()
    since_ms = 1610000000000
    # Test fetch_funding_rate_history (historical data)
    await exchange._fetch_funding_rate_history(
        pair="BTC/USDT:USDT",
        timeframe="4h",
        limit=limit,
        since_ms=since_ms,
    )

    assert api_mock.fetch_funding_rate_history.call_count == 1
    assert api_mock.fetch_funding_rate_history.call_args_list[0][0][0] == "BTC/USDT:USDT"
    kwargs = api_mock.fetch_funding_rate_history.call_args_list[0][1]
    assert kwargs["since"] == since_ms


def test_bitget_get_funding_fees(default_conf, mocker):
    now = datetime.now(timezone.utc)
    exchange = get_patched_exchange(mocker, default_conf, exchange="bitget")
    exchange._fetch_and_calculate_funding_fees = MagicMock()
    exchange.get_funding_fees("BTC/USDT:USDT", 1, False, now)
    assert exchange._fetch_and_calculate_funding_fees.call_count == 0

    default_conf["trading_mode"] = "futures"
    default_conf["margin_mode"] = "isolated"
    exchange = get_patched_exchange(mocker, default_conf, exchange="bitget")
    exchange._fetch_and_calculate_funding_fees = MagicMock()
    exchange.get_funding_fees("BTC/USDT:USDT", 1, False, now)

    assert exchange._fetch_and_calculate_funding_fees.call_count == 1


def test_bitget_fetch_orders(default_conf, mocker, limit_order):
    api_mock = MagicMock()
    api_mock.fetch_orders = MagicMock(
        return_value=[
            limit_order["buy"],
            limit_order["sell"],
        ]
    )
    api_mock.fetch_open_orders = MagicMock(return_value=[limit_order["buy"]])
    api_mock.fetch_closed_orders = MagicMock(return_value=[limit_order["buy"]])
    api_mock.is_unified_enabled = MagicMock(return_value=False)

    mocker.patch(f"{EXMS}.exchange_has", return_value=True)
    start_time = datetime.now(timezone.utc) - timedelta(days=20)

    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange="bitget")
    # Not available in dry-run
    assert exchange.fetch_orders("mocked", start_time) == []
    assert api_mock.fetch_orders.call_count == 0
    default_conf["dry_run"] = False

    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange="bitget")
    res = exchange.fetch_orders("mocked", start_time)
    # Bitget will call the endpoint 3 times, as it has a limit of 7 days per call
    assert api_mock.fetch_orders.call_count == 3
    assert api_mock.fetch_open_orders.call_count == 0
    assert api_mock.fetch_closed_orders.call_count == 0
    assert len(res) == 2 * 3


def test_bitget_fetch_order(default_conf_usdt, mocker):
    default_conf_usdt["dry_run"] = False

    api_mock = MagicMock()
    api_mock.fetch_order = MagicMock(
        return_value={
            "id": "123",
            "symbol": "BTC/USDT",
            "status": "closed",
            "filled": 20.0,
            "average": None,
            "price": 10000,
        }
    )
    api_mock.is_unified_enabled = MagicMock(return_value=False)
    mocker.patch(f"{EXMS}.exchange_has", return_value=True)
    exchange = get_patched_exchange(mocker, default_conf_usdt, api_mock, exchange="bitget")

    res = exchange.fetch_order("123", "BTC/USDT")
    assert res["price"] == 10000
    assert res["filled"] == 20.0
    assert res["status"] == "closed"

    api_mock.fetch_order = MagicMock(
        return_value={
            "id": "123",
            "symbol": "BTC/USDT",
            "status": "open",
            "filled": 0.0,
            "average": 10000,
            "price": 10000,
        }
    )

    res1 = exchange.fetch_order("123", "BTC/USDT")
    assert res1["average"] == 10000
    assert res1["filled"] == 0.0
    assert res1["status"] == "open"


def test__set_leverage_bitget(mocker, default_conf):
    api_mock = MagicMock()
    api_mock.set_leverage = MagicMock()
    type(api_mock).has = PropertyMock(return_value={"setLeverage": True})
    default_conf["dry_run"] = False
    default_conf["trading_mode"] = TradingMode.FUTURES
    default_conf["margin_mode"] = MarginMode.ISOLATED

    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange="bitget")
    exchange._lev_prep("BTC/USDT:USDT", 3, "buy")
    assert api_mock.set_leverage.call_count == 1
    # Leverage is rounded to 3.
    assert api_mock.set_leverage.call_args_list[0][1]["leverage"] == 3
    assert api_mock.set_leverage.call_args_list[0][1]["symbol"] == "BTC/USDT:USDT"


def test_load_leverage_tiers_bitget(default_conf, mocker, markets, tmp_path, caplog, time_machine):
    default_conf["datadir"] = tmp_path
    api_mock = MagicMock()
    type(api_mock).has = PropertyMock(
        return_value={
            "fetchLeverageTiers": False,
            "fetchMarketLeverageTiers": True,
        }
    )
    api_mock.fetch_market_leverage_tiers = AsyncMock(
        side_effect=[
            [
                {
                    "tier": 1,
                    "currency": "USDT",
                    "minNotional": 0,
                    "maxNotional": 500,
                    "maintenanceMarginRate": 0.02,
                    "maxLeverage": 75,
                    "info": {
                        "symbol": "ADAUSDT",
                        "level": "1",
                        "startUnit": "0",
                        "endUnit": "500",
                        "leverage": "75",
                        "keepMarginRate": "0.02",
                    },
                },
                {
                    "tier": 2,
                    "currency": "USDT",
                    "minNotional": 501,
                    "maxNotional": 1000,
                    "maintenanceMarginRate": 0.025,
                    "maxLeverage": 50,
                    "info": {
                        "symbol": "ADAUSDT",
                        "level": "2",
                        "startUnit": "501",
                        "endUnit": "1000",
                        "leverage": "50",
                        "keepMarginRate": "0.025",
                    },
                },
                {
                    "tier": 3,
                    "currency": "USDT",
                    "minNotional": 1001,
                    "maxNotional": 2000,
                    "maintenanceMarginRate": 0.03,
                    "maxLeverage": 20,
                    "info": {
                        "symbol": "ADAUSDT",
                        "level": "3",
                        "startUnit": "1001",
                        "endUnit": "2000",
                        "leverage": "20",
                        "keepMarginRate": "0.03",
                    },
                },
            ],
            TemporaryError("this Failed"),
            [
                {
                    "tier": 1,
                    "currency": "USDT",
                    "minNotional": 0,
                    "maxNotional": 2000,
                    "maintenanceMarginRate": 0.01,
                    "maxLeverage": 75,
                    "info": {
                        "symbol": "ETHUSDT",
                        "level": "1",
                        "startUnit": "0",
                        "endUnit": "2000",
                        "leverage": "75",
                        "keepMarginRate": "0.01",
                    },
                },
                {
                    "tier": 2,
                    "currency": "USDT",
                    "minNotional": 2001,
                    "maxNotional": 4000,
                    "maintenanceMarginRate": 0.015,
                    "maxLeverage": 50,
                    "info": {
                        "symbol": "ETHUSDT",
                        "level": "2",
                        "startUnit": "2001",
                        "endUnit": "4000",
                        "leverage": "50",
                        "keepMarginRate": "0.015",
                    },
                },
                {
                    "tier": 3,
                    "currency": "USDT",
                    "minNotional": 4001,
                    "maxNotional": 8000,
                    "maintenanceMarginRate": 0.02,
                    "maxLeverage": 20,
                    "info": {
                        "symbol": "ETHUSDT",
                        "level": "3",
                        "startUnit": "4001",
                        "endUnit": "8000",
                        "leverage": "20",
                        "keepMarginRate": "0.02",
                    },
                },
            ],
        ]
    )
    default_conf["trading_mode"] = "futures"
    default_conf["margin_mode"] = "isolated"
    default_conf["stake_currency"] = "USDT"
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange="bitget")
    exchange.trading_mode = TradingMode.FUTURES
    exchange.margin_mode = MarginMode.ISOLATED
    exchange.markets = markets

    # Initialization of load_leverage_tiers happens as part of exchange init.
    assert exchange._leverage_tiers == {
        "ADA/USDT:USDT": [
            {
                "minNotional": 0,
                "maxNotional": 500,
                "maintenanceMarginRate": 0.02,
                "maxLeverage": 75,
                "maintAmt": None,
            },
            {
                "minNotional": 501,
                "maxNotional": 1000,
                "maintenanceMarginRate": 0.025,
                "maxLeverage": 50,
                "maintAmt": None,
            },
            {
                "minNotional": 1001,
                "maxNotional": 2000,
                "maintenanceMarginRate": 0.03,
                "maxLeverage": 20,
                "maintAmt": None,
            },
        ],
        "ETH/USDT:USDT": [
            {
                "minNotional": 0,
                "maxNotional": 2000,
                "maintenanceMarginRate": 0.01,
                "maxLeverage": 75,
                "maintAmt": None,
            },
            {
                "minNotional": 2001,
                "maxNotional": 4000,
                "maintenanceMarginRate": 0.015,
                "maxLeverage": 50,
                "maintAmt": None,
            },
            {
                "minNotional": 4001,
                "maxNotional": 8000,
                "maintenanceMarginRate": 0.02,
                "maxLeverage": 20,
                "maintAmt": None,
            },
        ],
    }
    filename = (
        default_conf["datadir"] / f"futures/leverage_tiers_{default_conf['stake_currency']}.json"
    )
    assert filename.is_file()

    logmsg = "Cached leverage tiers are outdated. Will update."
    assert not log_has(logmsg, caplog)

    api_mock.fetch_market_leverage_tiers.reset_mock()

    exchange.load_leverage_tiers()
    assert not log_has(logmsg, caplog)

    assert api_mock.fetch_market_leverage_tiers.call_count == 0
    # 2 day passes ...
    time_machine.move_to(datetime.now() + timedelta(weeks=5))
    exchange.load_leverage_tiers()

    assert log_has(logmsg, caplog)


def test_get_max_pair_stake_amount_bitget(default_conf, mocker, leverage_tiers):
    exchange = get_patched_exchange(mocker, default_conf, exchange="bitget")
    assert exchange.get_max_pair_stake_amount("BNB/BUSD", 1.0) == float("inf")

    default_conf["trading_mode"] = "futures"
    default_conf["margin_mode"] = "isolated"
    exchange = get_patched_exchange(mocker, default_conf, exchange="bitget")
    exchange._leverage_tiers = leverage_tiers

    assert exchange.get_max_pair_stake_amount("XRP/USDT:USDT", 1.0) == 30000000
    assert exchange.get_max_pair_stake_amount("BNB/USDT:USDT", 1.0) == 50000000
    assert exchange.get_max_pair_stake_amount("BTC/USDT:USDT", 1.0) == 1000000000
    assert exchange.get_max_pair_stake_amount("BTC/USDT:USDT", 1.0, 10.0) == 100000000

    assert exchange.get_max_pair_stake_amount("TTT/USDT:USDT", 1.0) == float("inf")  # Not in tiers


def test_bitget_ohlcv_candle_limit(default_conf, mocker):
    exchange = get_patched_exchange(mocker, default_conf, exchange="bitget")
    timeframes = ("1m", "5m", "1h")
    start_time = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

    for timeframe in timeframes:
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.SPOT) == 1000
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.FUTURES) == 1000
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.MARK) == 200
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.FUNDING_RATE) == 100

        assert exchange.ohlcv_candle_limit(timeframe, CandleType.SPOT, start_time) == 1000
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.FUTURES, start_time) == 1000
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.MARK, start_time) == 200
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.FUNDING_RATE, start_time) == 100
        one_call = int((datetime.now(timezone.utc) - timedelta(days=29)).timestamp() * 1000)

        assert exchange.ohlcv_candle_limit(timeframe, CandleType.SPOT, one_call) == 1000
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.FUTURES, one_call) == 1000

        one_call = int((datetime.now(timezone.utc) - timedelta(days=32)).timestamp() * 1000)
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.SPOT, one_call) == 1000
        assert exchange.ohlcv_candle_limit(timeframe, CandleType.FUTURES, one_call) == 1000
