"""Tests for v1 retrofit model basics."""
import numpy as np
import pytest


# These imports will fail until the package is created - that's the RED phase
def test_v1_params_creation():
    from retrofit_v1 import Params
    p = Params(n=1000, n_co_ops=10, E=100000, tau=100, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42)
    assert p.n == 1000
    assert p.n_co_ops == 10
    assert p.E == 100000
    assert p.tau == 100
    assert p.surplus == 0.2
    assert p.mean_time == 12
    assert p.time_var == 4
    assert p.week_cost == 1000
    assert p.run_time == 5200
    assert p.seed == 42


def test_v1_params_validation():
    from retrofit_v1 import Params

    # Test positive validation
    with pytest.raises(ValueError):
        Params(n=0, n_co_ops=10, E=100000, tau=100, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42)

    with pytest.raises(ValueError):
        Params(n=1000, n_co_ops=10, E=-1000, tau=100, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42)

    # Test probability validation
    with pytest.raises(ValueError):
        Params(n=1000, n_co_ops=10, E=100000, tau=100, surplus=1.5,
               mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42)

    with pytest.raises(ValueError):
        Params(n=1000, n_co_ops=10, E=100000, tau=100, surplus=-0.1,
               mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42)

    # Test integer validation
    with pytest.raises(ValueError):
        Params(n=1000.5, n_co_ops=10, E=100000, tau=100, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42)


def test_v1_run_returns_result():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2,
               mean_time=10, time_var=3, week_cost=500, run_time=520, seed=123)
    result = run_simulation(p)
    assert hasattr(result, 'finished')
    assert hasattr(result, 'weekly_to_do')
    assert hasattr(result, 'weekly_queued')
    assert hasattr(result, 'weekly_in_progress')
    assert hasattr(result, 'weekly_finished')
    assert hasattr(result, 'weekly_total_accounts')
    assert hasattr(result, 'weekly_with_capacity')
    assert hasattr(result, 'total_weeks')
    assert hasattr(result, 'final_total_accounts')
    assert result.finished <= p.n
    assert result.total_weeks > 0
    assert result.final_total_accounts >= 0


def test_v1_seed_reproducibility():
    from retrofit_v1 import Params, run_simulation
    p1 = Params(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2,
                mean_time=12, time_var=4, week_cost=1000, run_time=1000, seed=999)
    p2 = Params(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2,
                mean_time=12, time_var=4, week_cost=1000, run_time=1000, seed=999)
    r1 = run_simulation(p1)
    r2 = run_simulation(p2)
    assert np.array_equal(r1.weekly_finished, r2.weekly_finished)
    assert np.array_equal(r1.weekly_to_do, r2.weekly_to_do)
    assert np.array_equal(r1.weekly_queued, r2.weekly_queued)
    assert np.array_equal(r1.weekly_in_progress, r2.weekly_in_progress)
    assert np.array_equal(r1.weekly_total_accounts, r2.weekly_total_accounts)
    assert r1.finished == r2.finished
    assert r1.total_weeks == r2.total_weeks
    assert r1.final_total_accounts == r2.final_total_accounts


def test_v1_mass_conservation():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=200, n_co_ops=3, E=80000, tau=15, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=2000, seed=1)
    r = run_simulation(p)
    for t in range(len(r.weekly_to_do)):
        total = (r.weekly_to_do[t] + r.weekly_queued[t] +
                 r.weekly_in_progress[t] + r.weekly_finished[t])
        assert total == p.n, f"Mass conservation violated at week {t}: {total} != {p.n}"


def test_v1_no_negative_accounts():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=10000, tau=5, surplus=0.1,
               mean_time=20, time_var=5, week_cost=2000, run_time=2000, seed=7)
    r = run_simulation(p)
    assert np.all(r.weekly_total_accounts >= 0), "Total accounts should never be negative"


def test_v1_finished_monotonic():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(np.diff(r.weekly_finished) >= 0), "Finished count should be monotonic"


def test_v1_to_do_monotonic_decrease():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(np.diff(r.weekly_to_do) <= 0), "To-do count should be monotonic decreasing"


def test_v1_queued_nonnegative():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(r.weekly_queued >= 0), "Queued count should never be negative"


def test_v1_completes_all_buildings_eventually():
    """With sufficient time and capital, all buildings should eventually be finished."""
    from retrofit_v1 import Params, run_simulation
    # Large endowment, many co-ops, long run time
    p = Params(n=100, n_co_ops=10, E=500000, tau=50, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=10000, seed=42)
    r = run_simulation(p)
    assert r.finished == p.n, f"Expected all {p.n} buildings finished, got {r.finished}"