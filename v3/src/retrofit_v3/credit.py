"""Credit access rule: how much can this household borrow? Pure function."""
from __future__ import annotations

CREDIT_ACCESS = ("income_tested", "open", "none")


def credit_limit(access: str, income: float, *, income_threshold: float, loan_to_income_cap: float) -> float:
    """Maximum loan (euros).

    income_tested: cap * income if income >= threshold, else 0.
    open:          cap * income for everyone.
    none:          0.
    """
    if access == "none":
        return 0.0
    if access == "open":
        return loan_to_income_cap * income
    if access == "income_tested":
        return loan_to_income_cap * income if income >= income_threshold else 0.0
    raise ValueError(f"unknown credit access rule {access!r}; expected one of {CREDIT_ACCESS}")
