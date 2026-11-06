"""Tax rebate: deduction capped by tax payable, arriving after a lag. Pure functions."""
from __future__ import annotations


def rebate_amount(cost: float, deduction_rate: float, tax_payable: float, refundable: bool = False) -> float:
    """Cash value of the rebate.

    Non-refundable: min(rate * cost, tax_payable): little tax means little back.
    Refundable:     rate * cost, whatever the tax payable.
    Never exceeds cost (rate <= 1 is validated in Params).
    """
    gross = max(0.0, deduction_rate * cost)
    if refundable:
        return min(gross, cost)
    return min(gross, max(0.0, tax_payable), cost)


def rebate_arrival_month(adoption_month: int, lag_months: int) -> int:
    return adoption_month + lag_months
