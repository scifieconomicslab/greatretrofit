"""Tests for v2 market realism and demographics."""
import numpy as np
import pytest


def test_v2_local_demand_signals():
    """Test that local demand signals work with neighbourhoods."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=4, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_neighbourhoods=4, enable_local_demand=True)
    r = run_simulation(p)
    assert hasattr(r, 'neighbourhood_time_on_market')
    assert r.neighbourhood_time_on_market is not None
    assert r.neighbourhood_time_on_market.shape == (4, len(r.weekly_finished))


def test_v2_income_process():
    """Test that income process parameters are accepted."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               income_ar1_rho=0.9, income_shock_sd=0.1, unemployment_prob=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'household_income_trajectories')


def test_v2_investor_market():
    """Test that investor market parameters are accepted."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_investors=True, investor_hurdle_mean=0.05, investor_hurdle_sd=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'investor_purchases')


def test_v2_stock_evolution():
    """Test that stock evolution parameters are accepted."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_construction=True, build_cost=150000, construction_lag_weeks=52)
    r = run_simulation(p)
    assert hasattr(r, 'new_construction_count')


def test_v2_demographics():
    """Test that demographic parameters are accepted."""
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_demographics=True, birth_rate=0.01, death_rate=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'population_trajectory')