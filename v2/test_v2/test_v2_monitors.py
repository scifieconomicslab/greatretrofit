"""Tests for v2 monitors and calibration."""
import numpy as np
import pytest


def test_v2_gini_wealth():
    """Test Gini wealth monitor."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=4, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert hasattr(r, 'gini_wealth')
    assert 0 <= r.gini_wealth <= 1, f"Gini should be in [0,1], got {r.gini_wealth}"
    assert hasattr(r, 'gini_wealth_trajectory')
    assert len(r.gini_wealth_trajectory) == r.total_weeks


def test_v2_price_dispersion():
    """Test price dispersion monitors."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=4, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_neighbourhoods=4)
    r = run_simulation(p)
    assert hasattr(r, 'price_dispersion_within')
    assert hasattr(r, 'price_dispersion_between')
    assert r.price_dispersion_within >= 0
    assert r.price_dispersion_between >= 0


def test_v2_cash_buyer_share():
    """Test cash buyer share monitor."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert hasattr(r, 'cash_buyer_share')
    assert 0 <= r.cash_buyer_share <= 1, f"Cash buyer share should be in [0,1], got {r.cash_buyer_share}"


def test_v2_time_on_market_spread():
    """Test time on market spread monitor."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert hasattr(r, 'time_on_market_spread')
    assert r.time_on_market_spread >= 0


def test_v2_bank_monitors():
    """Test bank-related monitors."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_banks=3, bank_ltv_mean=0.8, bank_ltv_sd=0.05, bank_spread_mean=0.02,
               enable_default=True)
    r = run_simulation(p)
    assert hasattr(r, 'bank_losses')
    assert hasattr(r, 'default_count')
    assert hasattr(r, 'total_loan_volume')
    assert r.bank_losses >= 0
    assert r.default_count >= 0
    assert r.total_loan_volume >= 0


def test_v2_investor_monitor():
    """Test investor purchase monitor."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_investors=True, investor_hurdle_mean=0.05, investor_hurdle_sd=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'investor_purchases')
    assert r.investor_purchases >= 0


def test_v2_construction_monitor():
    """Test new construction monitor."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_construction=True, build_cost=150000, construction_lag_weeks=52)
    r = run_simulation(p)
    assert hasattr(r, 'new_construction_count')
    assert r.new_construction_count >= 0


def test_v2_population_monitor():
    """Test population trajectory monitor."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_demographics=True, birth_rate=0.01, death_rate=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'population_trajectory')
    assert len(r.population_trajectory) == r.total_weeks
    assert all(p >= 0 for p in r.population_trajectory)


def test_v2_income_trajectory_monitor():
    """Test household income trajectory monitor."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               income_ar1_rho=0.9, income_shock_sd=0.1, unemployment_prob=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'household_income_trajectories')
    assert r.household_income_trajectories.shape[1] == r.total_weeks
    assert r.household_income_trajectories.shape[0] <= 100  # Sample size