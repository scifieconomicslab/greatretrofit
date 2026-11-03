"""Tests for v2 retrofit model basics."""
import numpy as np
import pytest


# These imports will fail until the package is created - that's the RED phase
def test_v2_params_creation():
    from retrofit_v2 import Params
    p = Params(n=1000, n_co_ops=10, E=100000, tau=100, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42,
               n_households=1000, income_mean=50000, income_cv=0.4, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=15)
    assert p.n_households == 1000
    assert p.income_mean == 50000
    assert p.income_cv == 0.4
    assert p.wealth_pareto_alpha == 1.5
    assert p.aspiration_mean == 50
    assert p.aspiration_sd == 15


def test_v2_run_returns_result():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=123,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    result = run_simulation(p)
    assert hasattr(result, 'finished')
    assert hasattr(result, 'weekly_to_do')
    assert hasattr(result, 'gini_wealth')  # new monitor
    assert hasattr(result, 'price_dispersion')  # new monitor


def test_v2_seed_reproducibility():
    from retrofit_v2 import Params, run_simulation
    base = dict(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2,
                mean_time=12, time_var=4, week_cost=1000, run_time=1000,
                n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                aspiration_mean=50, aspiration_sd=15)
    r1 = run_simulation(Params(**base, seed=999))
    r2 = run_simulation(Params(**base, seed=999))
    assert np.array_equal(r1.weekly_finished, r2.weekly_finished)
    assert np.array_equal(r1.weekly_to_do, r2.weekly_to_do)
    assert np.array_equal(r1.weekly_queued, r2.weekly_queued)
    assert np.array_equal(r1.weekly_in_progress, r2.weekly_in_progress)
    assert np.array_equal(r1.weekly_total_accounts, r2.weekly_total_accounts)
    assert r1.finished == r2.finished
    assert r1.total_weeks == r2.total_weeks
    assert r1.final_total_accounts == r2.final_total_accounts


def test_v2_mass_conservation():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=3, E=80000, tau=15, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    for t in range(len(r.weekly_to_do)):
        total = (r.weekly_to_do[t] + r.weekly_queued[t] +
                 r.weekly_in_progress[t] + r.weekly_finished[t])
        assert total == p.n, f"Mass conservation violated at week {t}: {total} != {p.n}"


def test_v2_no_negative_accounts():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=10000, tau=5, surplus=0.1,
               mean_time=20, time_var=5, week_cost=2000, run_time=2000, seed=7,
               n_households=100, income_mean=30000, income_cv=0.4, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert np.all(r.weekly_total_accounts >= 0), "Total accounts should never be negative"


def test_v2_gini_wealth_bounds():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=123,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert 0 <= r.gini_wealth <= 1, f"Gini should be in [0,1], got {r.gini_wealth}"