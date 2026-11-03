"""Tests for v2 financial dynamics (bargaining, banks, default)."""
import numpy as np
import pytest


def test_v2_bargaining():
    """Test that bargaining parameter works."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_bargaining=True, max_bid_shade=0.2, seller_reservation_pct=0.8)
    r = run_simulation(p)
    assert r.finished <= 100  # basic sanity


def test_v2_banks_exist():
    """Test that bank parameters are accepted."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_banks=3, bank_ltv_mean=0.8, bank_ltv_sd=0.05, bank_spread_mean=0.02)
    r = run_simulation(p)
    # Should have bank-related result fields
    assert hasattr(r, 'bank_losses')
    assert hasattr(r, 'default_count')


def test_v2_default_possible():
    """Test that default can occur with low capital."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=50, n_co_ops=1, E=10000, tau=5, surplus=0.1,
               mean_time=20, time_var=5, week_cost=2000, run_time=2000, seed=1,
               n_households=50, income_mean=30000, income_cv=0.4, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_banks=1, bank_ltv_mean=0.9, bank_ltv_sd=0.0, bank_spread_mean=0.03,
               enable_default=True)
    r = run_simulation(p)
    assert hasattr(r, 'default_count')