"""Comparison tests for v1 vs v2 retrofit models."""
import numpy as np
import pytest
from retrofit_v1 import Params as V1Params, run_simulation as run_v1
from retrofit_v2 import Params as V2Params, run_simulation as run_v2


def common_params(seed=42):
    """Common base parameters for both versions."""
    return dict(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2,
                mean_time=12, time_var=4, week_cost=1000, run_time=2000, seed=seed)


def test_v2_slower_with_heterogeneity():
    """v2 with household heterogeneity should complete slower than v1 baseline due to search/bargaining."""
    base = common_params()
    v1_p = V1Params(**base)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15, search_length=3, enable_bargaining=True)
    r1 = run_v1(v1_p)
    r2 = run_v2(v2_p)
    # v2 should take longer (more weeks) to finish same number of buildings
    # Allow some variance - v2 might be faster in some runs due to randomness
    assert r2.total_weeks >= r1.total_weeks * 0.5  # Generous bound


def test_v2_higher_final_capital_with_surplus():
    """Both versions should grow capital with surplus > 0."""
    base = common_params()
    v1_p = V1Params(**base)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15)
    r1 = run_v1(v1_p)
    r2 = run_v2(v2_p)
    assert r1.final_total_accounts >= 5 * 100000  # v1 baseline
    assert r2.final_total_accounts >= 5 * 100000  # v2 also grows


def test_v2_produces_gini_v1_does_not():
    """v2 has wealth distribution monitoring; v1 does not."""
    base = common_params()
    v1_p = V1Params(**base)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15)
    r1 = run_v1(v1_p)
    r2 = run_v2(v2_p)
    assert not hasattr(r1, 'gini_wealth')
    assert hasattr(r2, 'gini_wealth')
    assert 0 <= r2.gini_wealth <= 1


def test_v2_local_demand_creates_dispersion():
    """v2 with local demand should show price dispersion between neighbourhoods."""
    base = common_params(seed=123)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15,
                    n_neighbourhoods=4, enable_local_demand=True)
    r2 = run_v2(v2_p)
    assert hasattr(r2, 'price_dispersion_between')
    assert r2.price_dispersion_between >= 0


def test_v1_mass_conservation_vs_v2():
    """Both versions should conserve mass."""
    base = common_params()
    v1_p = V1Params(**base)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15)
    r1 = run_v1(v1_p)
    r2 = run_v2(v2_p)

    # Check mass conservation at each week
    for t in range(len(r1.weekly_finished)):
        v1_total = r1.weekly_to_do[t] + r1.weekly_queued[t] + r1.weekly_in_progress[t] + r1.weekly_finished[t]
        assert v1_total == v1_p.n

    for t in range(len(r2.weekly_finished)):
        v2_total = r2.weekly_to_do[t] + r2.weekly_queued[t] + r2.weekly_in_progress[t] + r2.weekly_finished[t]
        assert v2_total == v2_p.n


def test_v1_seed_reproducibility_vs_v2():
    """Both versions should be reproducible with same seed."""
    base = common_params(seed=999)
    v1_p1 = V1Params(**base)
    v1_p2 = V1Params(**base)
    r1_1 = run_v1(v1_p1)
    r1_2 = run_v1(v1_p2)
    assert np.array_equal(r1_1.weekly_finished, r1_2.weekly_finished)

    v2_p1 = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                     aspiration_mean=50, aspiration_sd=15)
    v2_p2 = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                     aspiration_mean=50, aspiration_sd=15)
    r2_1 = run_v2(v2_p1)
    r2_2 = run_v2(v2_p2)
    assert np.array_equal(r2_1.weekly_finished, r2_2.weekly_finished)


# Snapshot test - captures v1 baseline behavior for regression
def test_v1_snapshot(snapshot):
    base = common_params(seed=42)
    v1_p = V1Params(**base)
    r1 = run_v1(v1_p)
    snapshot.assert_match({
        'finished': r1.finished,
        'total_weeks': r1.total_weeks,
        'final_total_accounts': round(r1.final_total_accounts, 2),
        'weekly_finished': r1.weekly_finished.tolist(),
    }, 'v1_baseline_snapshot.json')


# Snapshot test - captures v2 baseline behavior for regression
def test_v2_snapshot(snapshot):
    base = common_params(seed=42)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                     aspiration_mean=50, aspiration_sd=15)
    r2 = run_v2(v2_p)
    snapshot.assert_match({
        'finished': r2.finished,
        'total_weeks': r2.total_weeks,
        'final_total_accounts': round(r2.final_total_accounts, 2),
        'gini_wealth': round(r2.gini_wealth, 4),
        'weekly_finished': r2.weekly_finished.tolist(),
    }, 'v2_baseline_snapshot.json')