"""Invariant tests for v1 retrofit model."""
import numpy as np
import pytest
from retrofit_v1 import Params, run_simulation


@pytest.mark.parametrize("n,n_coops,E,tau,surplus", [
    (100, 1, 50000, 5, 0.1),
    (500, 5, 100000, 20, 0.2),
    (1000, 10, 200000, 50, 0.3),
])
def test_surplus_grows_capital(n, n_coops, E, tau, surplus):
    """With surplus > 0 and completion, total capital should grow."""
    p = Params(n=n, n_co_ops=n_coops, E=E, tau=tau, surplus=surplus,
               mean_time=12, time_var=4, week_cost=1000, run_time=5000, seed=42)
    r = run_simulation(p)
    if r.finished == n:  # only check if completed
        assert r.final_total_accounts >= n_coops * E, \
            f"Capital should grow: {r.final_total_accounts} < {n_coops * E}"


def test_monotonic_finished():
    """Finished count should never decrease."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(np.diff(r.weekly_finished) >= 0)


def test_to_do_monotonic_decrease():
    """To-do count should never increase."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(np.diff(r.weekly_to_do) <= 0)


def test_queued_nonnegative():
    """Queued count should never be negative."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(r.weekly_queued >= 0)


def test_in_progress_nonnegative():
    """In-progress count should never be negative."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(r.weekly_in_progress >= 0)


def test_total_accounts_nonnegative():
    """Total accounts should never be negative."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(r.weekly_total_accounts >= 0)


def test_finished_bounded_by_n():
    """Finished count should never exceed total buildings."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(r.weekly_finished <= p.n)


def test_weekly_arrays_same_length():
    """All weekly arrays should have the same length."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    lengths = [len(r.weekly_to_do), len(r.weekly_queued), len(r.weekly_in_progress),
               len(r.weekly_finished), len(r.weekly_total_accounts), len(r.weekly_with_capacity)]
    assert all(l == lengths[0] for l in lengths)


def test_total_weeks_matches_array_length():
    """total_weeks should match the length of weekly arrays."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert r.total_weeks == len(r.weekly_finished)


def test_final_accounts_matches_last_weekly():
    """final_total_accounts should match the last weekly_total_accounts."""
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2,
               mean_time=12, time_var=4, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert abs(r.final_total_accounts - r.weekly_total_accounts[-1]) < 1e-9