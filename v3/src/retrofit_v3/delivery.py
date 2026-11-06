"""Delivery-mode strategies: what the household pays, what the state pays, when."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .rebate import rebate_amount


@dataclass(frozen=True)
class QuoteContext:
    base_cost: float        # labour + materials for this unit, before margin/overhead
    tax_payable: float
    income_quintile: int    # 1..5
    params: "object"        # Params (explicit input; strategies read levers from it)


@dataclass(frozen=True)
class Quote:
    eligible: bool               # the public scheme applies to this household (False: bought on the market, no subsidy)
    price: float                 # total paid to whoever does the work
    household_upfront: float     # what the household must finance now
    requires_financing: bool
    state_pays_now: float        # paid to the provider at adoption
    rebate: float                # deferred transfer to household
    rebate_lag_months: int
    capacity_limited: bool       # uses public-service capacity


class DeliveryMode(ABC):
    name: str

    @abstractmethod
    def quote(self, ctx: QuoteContext) -> Quote: ...


def _eligible(ctx) -> bool:
    p = ctx.params
    return (not p.means_test) or ctx.income_quintile <= p.means_test_max_quintile


def _market_quote(ctx) -> Quote:
    """A household the public scheme does not cover buys on the market: full price with margin, own financing, no subsidy."""
    p = ctx.params
    price = ctx.base_cost * (1.0 + p.vendor_margin)
    return Quote(False, price, price, True, 0.0, 0.0, 0, False)


class RebateMarket(DeliveryMode):
    name = "rebate_market"

    def quote(self, ctx):
        p = ctx.params
        if not _eligible(ctx):
            return _market_quote(ctx)
        price = ctx.base_cost * (1.0 + p.vendor_margin)
        reb = rebate_amount(price, p.deduction_rate, ctx.tax_payable, p.refundable)
        return Quote(True, price, price, True, 0.0, reb, p.rebate_lag_months, False)


class Passthrough(DeliveryMode):
    name = "passthrough"

    def quote(self, ctx):
        p = ctx.params
        if not _eligible(ctx):
            return _market_quote(ctx)
        price = ctx.base_cost * (1.0 + p.vendor_margin)
        return Quote(True, price, 0.0, False, price, 0.0, 0, False)


class PublicService(DeliveryMode):
    name = "public_service"

    def quote(self, ctx):
        p = ctx.params
        if not _eligible(ctx):
            return _market_quote(ctx)
        price = ctx.base_cost * (1.0 + p.public_overhead)
        return Quote(True, price, 0.0, False, price, 0.0, 0, True)


DELIVERY = {m.name: m() for m in (RebateMarket, Passthrough, PublicService)}
