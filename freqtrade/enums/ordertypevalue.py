from enum import Enum


class OrderTypeValues(str, Enum):
    limit = "limit"
    market = "market"
    trigger_limit = "trigger_limit"
    trigger_market = "trigger_market"
