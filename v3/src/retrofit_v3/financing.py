"""Financing an upfront price from savings plus credit. Pure functions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinancingPlan:
    from_savings: float
    loan: float
    feasible: bool


def plan_financing(upfront: float, savings: float, credit_limit: float,
                   savings_usable_share: float = 1.0) -> FinancingPlan:
    """Savings first, remainder by loan; feasible iff the loan fits the credit limit."""
    usable = max(0.0, savings) * savings_usable_share
    from_savings = min(usable, upfront)
    loan = upfront - from_savings
    return FinancingPlan(from_savings, loan, loan <= credit_limit + 1e-9)


def loan_payment(principal: float, annual_rate: float, months: int) -> float:
    """Level monthly annuity payment."""
    if principal <= 0 or months <= 0:
        return 0.0
    r = (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0
    if r == 0.0:
        return principal / months
    return principal * r / (1.0 - (1.0 + r) ** -months)
