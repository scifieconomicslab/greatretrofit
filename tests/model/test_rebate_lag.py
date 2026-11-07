"""SM-1 regression: rebate_lag_months = 0 (slider minimum) used to lose every rebate.

Semantics (Python and JS identical): lag L >= 1 delivers a rebate in step t + L (visible in frame t + L + 1); lag 0 delivers it in the
month of the retrofit (frame t + 1). A fractional lag (API only) is rounded half to even to whole months by Params. All numbers are placeholders.
"""
import math
from dataclasses import replace

import pytest

from node_util import needs_node, run_node
from retrofit_v3 import Params, run_simulation
from retrofit_v3.model import Simulation

# saving_per_m2_year is high so that every adoption has a positive NPV whatever the lag: the sequence of adoptions is then the same for every lag
# and the lags differ only in WHEN the same rebates arrive.
CFG = dict(n_buildings=30, horizon_months=120, credit_access="open", deduction_rate=0.5, saving_per_m2_year=200.0, delivery_mode="rebate_market", seed=3)
LAGS = list(range(0, 25))


def python_sweep(lags):
    out = []
    for lag in lags:
        sim = Simulation(Params(**CFG, rebate_lag_months=lag))
        for _ in range(CFG["horizon_months"]):
            sim.step()
        out.append(dict(lag=lag, effective_lag=sim.p.rebate_lag_months, n_events=len(sim.events), entitled=sum(e.rebate for e in sim.events),
                        public_cost=sim.frame["series"]["public_cost"], cash_total=sum(u.cash_net for u in sim.units),
                        queued=sum(c for v in sim.pending.values() for _, c in v), stale_keys=sum(1 for m in sim.pending if m < sim.t),
                        event_keys=[[e.month, e.unit] for e in sim.events], net_cash=sim.frame["series"]["net_cash_by_quintile"], sim=sim))
    return out


@pytest.fixture(scope="module")
def sweep():
    return python_sweep(LAGS)


def test_lag_zero_is_paid_in_the_month_of_the_retrofit():
    r = run_simulation(Params(**{**CFG, "horizon_months": 60}, rebate_lag_months=0))
    entitled = sum(e.rebate for e in r.events)
    assert entitled > 0
    assert r.final_frame["series"]["public_cost"] == pytest.approx(entitled)
    # visible in the very next frame
    first = min(e.month for e in r.events if e.rebate > 0)
    assert r.frames[first]["series"]["public_cost"] == 0.0
    assert r.frames[first + 1]["series"]["public_cost"] > 0.0


def test_no_rebate_stranded_in_the_queue_for_any_lag(sweep):
    for row in sweep:
        assert row["stale_keys"] == 0, f"lag {row['lag']}: {row['stale_keys']} queue key(s) in the past"


def test_sweep_adoptions_do_not_depend_on_lag(sweep):
    """Precondition of the sweep below: with these parameters the rebate arrives later but the decisions are the same."""
    assert len({tuple(map(tuple, r["event_keys"])) for r in sweep}) == 1
    assert sweep[0]["n_events"] > 20


def test_sweep_total_rebates_paid_equal_across_lags_when_horizon_is_long_enough(sweep):
    """Rebates for retrofits up to month 120 - 1 - 24 have arrived at the horizon for every lag 0..24: that sum is the same for every lag,
    and nothing is lost: delivered (public cost) + still queued == everything entitled."""
    cutoff = CFG["horizon_months"] - 1 - max(LAGS)
    early = [sum(e.rebate for e in r["sim"].events if e.month <= cutoff) for r in sweep]
    assert early[0] > 0 and all(x == pytest.approx(early[0], rel=1e-12) for x in early)
    for r in sweep:
        lag = r["lag"]
        arrived = sum(e.rebate for e in r["sim"].events if e.month + lag <= CFG["horizon_months"] - 1)
        assert r["public_cost"] == pytest.approx(arrived, rel=1e-12), lag               # public-cost series includes every due rebate
        assert r["public_cost"] + r["queued"] == pytest.approx(r["entitled"], rel=1e-12), lag   # none lost
        assert r["public_cost"] >= early[0] * (1 - 1e-12), lag                           # every lag has paid at least the early ones
    # a later lag can only have paid less by the horizon
    costs = [r["public_cost"] for r in sweep]
    assert all(a >= b - 1e-9 for a, b in zip(costs, costs[1:]))


def test_sweep_household_cash_gets_the_rebate(sweep):
    """Household net cash differs between lags exactly by the rebates not yet arrived: cash(L) - cash(24) == public_cost(L) - public_cost(24)."""
    last = sweep[-1]
    for r in sweep:
        assert r["cash_total"] - last["cash_total"] == pytest.approx(r["public_cost"] - last["public_cost"], abs=1e-6), r["lag"]


def test_fractional_lag_is_rounded_half_to_even_and_not_lost():
    expect = {0.0: 0, 0.4: 0, 0.5: 0, 0.6: 1, 1.5: 2, 2.5: 2, 3.5: 4, 23.6: 24}
    for raw, want in expect.items():
        assert Params(rebate_lag_months=raw).rebate_lag_months == want, raw
    rows = python_sweep([1.5, 2])
    assert rows[0]["effective_lag"] == 2 and rows[0]["public_cost"] == pytest.approx(rows[1]["public_cost"])
    assert rows[0]["stale_keys"] == 0 and isinstance(Params(rebate_lag_months=1.5).rebate_lag_months, int)


@pytest.mark.parametrize("bad", [-1, -0.5, float("nan"), float("inf")])
def test_bad_lag_is_rejected(bad):
    with pytest.raises(ValueError):
        Params(rebate_lag_months=bad)


@needs_node
def test_js_agrees_with_python_on_the_sweep(sweep):
    lags = LAGS + [0.5, 1.5, 2.5]
    py = {r["lag"]: r for r in sweep} | {r["lag"]: r for r in python_sweep([0.5, 1.5, 2.5])}
    js = run_node("rebate_lag_sweep.js", __import__("json").dumps(lags))
    assert len(js) == len(lags)
    for j in js:
        p = py[j["lag"]]
        assert j["effective_lag"] == p["effective_lag"], j["lag"]
        assert j["event_keys"] == p["event_keys"], j["lag"]
        assert j["stale_keys"] == 0
        for k in ("entitled", "public_cost", "cash_total", "queued"):
            assert j[k] == pytest.approx(p[k], rel=1e-9, abs=1e-9), (j["lag"], k)
        for a, b in zip(j["net_cash"], p["net_cash"]):
            assert (a is None) == (b is None) and (a is None or a == pytest.approx(b, rel=1e-9, abs=1e-9)), j["lag"]
