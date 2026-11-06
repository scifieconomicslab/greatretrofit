"""Household NPV of a retrofit. Pure functions, explicit inputs, monthly units."""
from __future__ import annotations


def monthly_rate(annual: float) -> float:
    """Compound-equivalent monthly rate."""
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def annuity_pv(first_payment: float, rate: float, n_months: int, growth: float = 0.0) -> float:
    """PV of a (growing) annuity paid at the end of months 1..n.

    first_payment is paid at month 1 and grows by `growth` per month.
    """
    if n_months <= 0 or first_payment == 0.0:
        return 0.0
    q = (1.0 + growth) / (1.0 + rate)
    if abs(q - 1.0) < 1e-12:
        return first_payment / (1.0 + rate) * n_months
    return first_payment / (1.0 + rate) * (1.0 - q ** n_months) / (1.0 - q)


def npv_retrofit(
    *,
    monthly_saving: float,
    horizon_months: int,
    monthly_discount: float,
    monthly_energy_growth: float,
    cash_from_savings: float,
    loan_payment: float,
    loan_months: int,
    rebate: float,
    rebate_lag_months: int,
) -> float:
    """NPV = PV(energy savings over horizon) + PV(rebate) - cash spent now - PV(loan payments).

    The loan principal is not a separate term: it funds part of the price, and
    the household's cost of that part is the PV of its payments.
    """
    pv_savings = annuity_pv(monthly_saving, monthly_discount, horizon_months, monthly_energy_growth)
    pv_rebate = rebate / (1.0 + monthly_discount) ** rebate_lag_months if rebate else 0.0
    pv_loan = annuity_pv(loan_payment, monthly_discount, loan_months)
    return pv_savings + pv_rebate - cash_from_savings - pv_loan
