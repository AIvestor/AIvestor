from dataclasses import dataclass
from typing import Literal

from freqtrade.constants import LongShort


# Used for Orders preparation for execution on exchange or backtesting
@dataclass
class OrderToCreate:
    pair: str
    type: Literal["limit", "market"]
    side: Literal["buy", "sell"]
    price: float
    amount: float
    stake_amount: float
    leverage: float
    order_tag: str
    reduce_only: bool
    time_in_force: Literal["GTC", "FOK", "IOC"]
    trade_side: LongShort


@dataclass
class OrderToValidate:
    type: Literal["limit", "market"]
    side: Literal["buy", "sell"]
    price: float
    amount: float
    action_side: Literal["entry", "exit"]
    time_in_force: Literal["GTC", "FOK", "IOC"]
    order_tag: str
    trade_side: LongShort
