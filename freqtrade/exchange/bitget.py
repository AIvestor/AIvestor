import logging
from datetime import datetime, timedelta, timezone

import ccxt

from freqtrade.constants import BuySell
from freqtrade.enums import CandleType, MarginMode, PriceType, TradingMode
from freqtrade.exceptions import ExchangeError
from freqtrade.exchange import Exchange
from freqtrade.exchange.exchange_types import FtHas, OHLCVResponse
from freqtrade.util.datetime_helpers import dt_now, dt_ts


logger = logging.getLogger(__name__)


class Bitget(Exchange):
    """
    Bitget exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.

    Please note that this exchange is not included in the list of exchanges
    officially supported by the Freqtrade development team. So some features
    may still not work as expected.
    """

    _ft_has: FtHas = {
        "ohlcv_candle_limit": 1000,
        "ohlcv_has_history": True,
        "order_time_in_force": ["GTC", "FOK", "IOC"],
        "trades_has_history": True,
    }
    _ft_has_futures: FtHas = {
        "ohlcv_has_history": True,
        "mark_ohlcv_timeframe": "4h",
        "funding_fee_timeframe": "8h",
        "stoploss_on_exchange": True,
        "stoploss_order_types": {"limit": "limit", "market": "market"},
        "stop_price_prop": "stopPrice",
        "stop_price_type_field": "triggerBy",
        "stop_price_type_value_mapping": {
            PriceType.LAST: "last_price",
            PriceType.MARK: "mark_price",
            PriceType.INDEX: "index_price",
        },
    }

    _supported_trading_mode_margin_pairs: list[tuple[TradingMode, MarginMode]] = [
        (TradingMode.FUTURES, MarginMode.ISOLATED)
    ]

    def _get_params(
        self,
        side: BuySell,
        ordertype: str,
        leverage: float,
        reduceOnly: bool,
        time_in_force: str = "GTC",
    ) -> dict:
        params = super()._get_params(
            side=side,
            ordertype=ordertype,
            leverage=leverage,
            reduceOnly=reduceOnly,
            time_in_force=time_in_force,
        )
        if self.trading_mode == TradingMode.FUTURES and self.margin_mode:
            params["marginMode"] = self.margin_mode.lower()
        return params

    def timeframe_to_milliseconds(self, timeframe: str) -> int:
        return ccxt.Exchange.parse_timeframe(timeframe) * 1000

    async def _async_get_historic_ohlcv(
        self,
        pair: str,
        timeframe: str,
        since_ms: int,
        candle_type: CandleType,
        raise_: bool = False,
        until_ms: int | None = None,
    ) -> OHLCVResponse:
        try:
            pair_data = await super()._async_get_historic_ohlcv(
                pair, timeframe, since_ms, candle_type, raise_, until_ms
            )

            pair, _, candle_type, data, partial_candle = pair_data

            if candle_type not in (CandleType.FUNDING_RATE):
                current_time = int(datetime.now(timezone.utc).timestamp() * 1000)
                timeframe_ms = self.timeframe_to_milliseconds(timeframe)
                last_candle_time = data[-1][0] if data else 0

                if current_time - last_candle_time >= timeframe_ms:
                    newest_candle_start = current_time - (current_time % timeframe_ms)

                    params = {}
                    if candle_type == CandleType.MARK:
                        params["price"] = "mark"
                    elif candle_type == CandleType.INDEX:
                        params["price"] = "index"

                    latest_candles = await self._api_async.fetch_ohlcv(
                        pair, timeframe, newest_candle_start, 1, params
                    )

                    if latest_candles:
                        data.append(latest_candles[0])
                    else:
                        estimated_candle = await self._estimate_current_candle(
                            pair, timeframe, newest_candle_start
                        )
                        if estimated_candle:
                            data.append(estimated_candle)
                        else:
                            logger.warning(f"can't for {pair} get candle of {timeframe}")

            return pair, timeframe, candle_type, data, partial_candle

        except Exception as e:
            logger.error(
                f"params：{pair}, {timeframe}, {since_ms}, {candle_type}, "
                f"can't get_historic_ohlcv: {e}"
            )
            raise

    async def _estimate_current_candle(
        self, pair: str, timeframe: str, start_time: int
    ) -> list[float]:
        timeframe_map: dict[str, tuple[str, int]] = {
            "5m": ("1m", 5),
            "15m": ("3m", 5),
            "30m": ("5m", 6),
            "1h": ("15m", 4),
            "4h": ("1h", 4),
            "6h": ("1h", 6),
            "12h": ("3h", 4),
            "1d": ("6h", 4),
            "1w": ("1d", 7),
            "1m": ("1w", 4),
        }

        if timeframe not in timeframe_map:
            raise Exception(f"{timeframe} not in timeframe list")

        smaller_tf, max_candles = timeframe_map[timeframe]

        try:
            smaller_candles = await self._api_async.fetch_ohlcv(
                pair, smaller_tf, start_time, max_candles
            )

            if not smaller_candles:
                logger.warning(f"can't get  {smaller_tf} candle data for {pair}")
                return []
            open_price = smaller_candles[0][1]
            high_price = max(candle[2] for candle in smaller_candles)
            low_price = min(candle[3] for candle in smaller_candles)
            close_price = smaller_candles[-1][4]
            volume = sum(candle[5] for candle in smaller_candles)
            return [start_time, open_price, high_price, low_price, close_price, volume]

        except Exception as e:
            raise Exception(f"can't for {pair} get candle of {timeframe}: {e}")

    def ohlcv_candle_limit(
        self, timeframe: str, candle_type: CandleType, since_ms: int | None = None
    ) -> int:
        if candle_type == CandleType.FUNDING_RATE:
            return 100  # Bitget seems to limit funding rate data to 100 entries
        if candle_type == CandleType.MARK:
            return 200
        # For other candle types, use the default or previously defined limit
        return super().ohlcv_candle_limit(timeframe, candle_type, since_ms)

    def get_funding_fees(
        self, pair: str, amount: float, is_short: bool, open_date: datetime
    ) -> float:
        if self.trading_mode == TradingMode.FUTURES:
            try:
                return self._fetch_and_calculate_funding_fees(pair, amount, is_short, open_date)
            except ExchangeError:
                logger.warning(f"Could not update funding fees for {pair}.")
        return 0.0

    def get_max_pair_stake_amount(self, pair: str, price: float, leverage: float = 1.0) -> float:
        if self.trading_mode == TradingMode.SPOT:
            return float("inf")  # Not actually inf, but this probably won't matter for SPOT

        if pair not in self._leverage_tiers:
            return float("inf")

        pair_tiers = self._leverage_tiers[pair]
        return pair_tiers[-1]["maxNotional"] / leverage

    def fetch_orders(self, pair: str, since: datetime, params: dict | None = None) -> list[dict]:
        orders = []

        while since < dt_now():
            until = since + timedelta(days=7, minutes=-1)
            orders += super().fetch_orders(pair, since, params={"until": dt_ts(until)})
            since = until

        return orders

    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> dict:
        order = super().fetch_order(order_id, pair, params)
        if not hasattr(order, "status"):
            return order
        if order["status"] == "closed" and order.get("average") is None and order.get("price"):
            order["average"] = order["price"]
        return order
