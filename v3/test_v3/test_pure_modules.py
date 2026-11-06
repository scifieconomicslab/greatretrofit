"""Unit tests for the pure decision modules."""
import pytest

from retrofit_v3.credit import credit_limit
from retrofit_v3.financing import loan_payment, plan_financing
from retrofit_v3.npv import annuity_pv, monthly_rate, npv_retrofit
from retrofit_v3.rebate import rebate_amount, rebate_arrival_month


def test_annuity_matches_direct_sum():
    r, g, n, p = 0.004, 0.002, 60, 100.0
    direct = sum(p * (1 + g) ** (k - 1) / (1 + r) ** k for k in range(1, n + 1))
    assert annuity_pv(p, r, n, g) == pytest.approx(direct)
    assert annuity_pv(p, 0.0, n) == pytest.approx(p * n)
    assert annuity_pv(p, r, 0) == 0.0


def test_npv_terms():
    kw = dict(monthly_saving=10.0, horizon_months=12, monthly_discount=0.0, monthly_energy_growth=0.0,
              cash_from_savings=0.0, loan_payment=0.0, loan_months=0, rebate=0.0, rebate_lag_months=0)
    assert npv_retrofit(**kw) == pytest.approx(120.0)
    assert npv_retrofit(**{**kw, "cash_from_savings": 50.0, "rebate": 20.0}) == pytest.approx(90.0)
    d = monthly_rate(0.04)
    assert npv_retrofit(**{**kw, "monthly_saving": 0.0, "rebate": 100.0, "rebate_lag_months": 12,
                           "monthly_discount": d}) == pytest.approx(100 / 1.04)


def test_credit_rules():
    kw = dict(income_threshold=20000.0, loan_to_income_cap=1.0)
    assert credit_limit("none", 50000, **kw) == 0
    assert credit_limit("open", 10000, **kw) == 10000
    assert credit_limit("income_tested", 10000, **kw) == 0
    assert credit_limit("income_tested", 30000, **kw) == 30000
    with pytest.raises(ValueError):
        credit_limit("bogus", 1, **kw)


def test_financing():
    p = plan_financing(1000, 400, 700)
    assert (p.from_savings, p.loan, p.feasible) == (400, 600, True)
    assert not plan_financing(1000, 400, 500).feasible
    assert plan_financing(1000, 5000, 0).feasible
    assert plan_financing(1000, 400, 700, savings_usable_share=0.5).loan == 800
    assert loan_payment(1200, 0.0, 12) == 100
    assert loan_payment(0, 0.05, 12) == 0


def test_rebate_capped_by_tax_and_cost():
    assert rebate_amount(1000, 0.3, 5000) == 300
    assert rebate_amount(1000, 0.3, 100) == 100          # tax capacity binds
    assert rebate_amount(1000, 0.3, 0) == 0
    assert rebate_amount(1000, 0.3, 0, refundable=True) == 300
    assert rebate_amount(1000, 1.0, 5000) == 1000
    assert rebate_arrival_month(5, 12) == 17
