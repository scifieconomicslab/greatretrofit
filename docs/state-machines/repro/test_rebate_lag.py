"""SM-1: a rebate with lag 0 (inside the manifest range 0..24) is queued for a month that has already been processed and never arrives.
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_rebate_lag.py -q
Expected today: 2 xfailed (strict: when the model is fixed these flip to XPASS and fail, telling you to drop the marker)."""
from dataclasses import replace

import pytest

from retrofit_v3 import Params, run_simulation
from retrofit_v3.model import Simulation

BASE = Params(n_buildings=30, horizon_months=60, credit_access="open", deduction_rate=0.5, delivery_mode="rebate_market")


def _entitled(r, lag, horizon):
    return sum(e.rebate for e in r.events if e.month + lag <= horizon - 1)


@pytest.mark.xfail(strict=True, reason="SM-1: lag 0 rebates are queued under the current month after it was popped (model.py:474 pops before 361 pushes) and are never delivered")
def test_lag_zero_rebate_reaches_public_cost():
    r = run_simulation(replace(BASE, rebate_lag_months=0))
    entitled = _entitled(r, 0, 60)
    assert entitled > 0
    assert r.final_frame["series"]["public_cost"] == pytest.approx(entitled)      # observed: 0.0


@pytest.mark.xfail(strict=True, reason="SM-1: the rebate queue keeps entries whose month is in the past")
def test_no_rebate_stranded_in_the_queue():
    sim = Simulation(replace(BASE, rebate_lag_months=0))
    for _ in range(60):
        sim.step()
    stale = {m: v for m, v in sim.pending.items() if m < sim.t}
    assert not stale, f"{sum(len(v) for v in stale.values())} rebate(s) due in past months {sorted(stale)[:5]}"


def test_lag_one_is_delivered_control():
    r = run_simulation(replace(BASE, rebate_lag_months=1))
    assert r.final_frame["series"]["public_cost"] == pytest.approx(_entitled(r, 1, 60))
