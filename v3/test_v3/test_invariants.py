"""Invariants that must hold whatever the economists answer."""
from dataclasses import replace

import pytest

from retrofit_v3 import Params, run_simulation
from retrofit_v3.frames import BUILDING_STATES

BASE = Params(n_buildings=60, horizon_months=84, keep_frames=True)
MODES = ["rebate_market", "passthrough", "public_service"]


def _final_adopted(p):
    return run_simulation(replace(p, keep_frames=False)).adopted_units


def test_seed_reproducibility():
    a, b = run_simulation(BASE), run_simulation(BASE)
    assert a.frames == b.frames and a.events == b.events
    c = run_simulation(replace(BASE, seed=1))
    assert c.events != a.events


def test_on_step_gets_every_frame():
    seen = []
    r = run_simulation(BASE, on_step=seen.append)
    assert len(seen) == BASE.horizon_months + 1 == len(r.frames)
    assert [f["t"] for f in seen] == list(range(BASE.horizon_months + 1))


@pytest.mark.parametrize("mode", MODES)
def test_state_count_conservation_and_unit_bounds(mode):
    r = run_simulation(replace(BASE, delivery_mode=mode))
    prev = {}
    for f in r.frames:
        assert sum(f["series"]["state_counts"].values()) == r.n_buildings == len(f["buildings"])
        for b in f["buildings"]:
            assert b["state"] in BUILDING_STATES
            assert 0 <= b["adopted_share"] <= 1
            assert b["adopted_share"] >= prev.get(b["id"], 0)   # never un-retrofit
            prev[b["id"]] = b["adopted_share"]
            assert (b["state"] == "retrofitted") == (b["adopted_share"] == 1 and b["tenure"] != "rental")
            if b["tenure"] == "rental":
                assert b["state"] == "not_modelled" and b["adopted_share"] == 0
        assert f["series"]["adopted_units"] == round(sum(b["adopted_share"] * b["units"] for b in f["buildings"]))


@pytest.mark.parametrize("refundable", [False, True])
@pytest.mark.parametrize("rate", [0.0, 0.3, 1.0])
def test_rebate_never_exceeds_cost_or_tax(rate, refundable):
    r = run_simulation(replace(BASE, deduction_rate=rate, refundable=refundable, vendor_margin=0.0))
    for e in r.events:
        assert e.rebate <= e.price + 1e-9
        assert e.rebate <= rate * e.price + 1e-9
        if not refundable:
            assert e.rebate <= e.tax_payable + 1e-9


@pytest.mark.parametrize("access", ["income_tested", "open", "none"])
def test_rebate_market_retrofit_is_financed(access):
    r = run_simulation(replace(BASE, credit_access=access))
    assert r.adopted_units > 0 or access == "none"
    for e in r.events:
        assert e.from_savings + e.loan == pytest.approx(e.price)
        assert e.from_savings <= e.savings_at_adoption + 1e-9
        assert e.loan <= e.credit_limit + 1e-9
        if access == "none":
            assert e.loan == 0


@pytest.mark.parametrize("mode", ["passthrough", "public_service"])
def test_state_funded_modes_need_no_financing(mode):
    r = run_simulation(replace(BASE, delivery_mode=mode, savings_scale=0.0, credit_access="none"))
    assert r.adopted_units > 0
    assert all(e.from_savings == 0 and e.loan == 0 and e.state_pays_now == pytest.approx(e.price) for e in r.events)


@pytest.mark.parametrize("cap", [0.0, 0.02, 0.1, 0.5])
def test_public_service_respects_capacity(cap):
    p = replace(BASE, delivery_mode="public_service", public_capacity=cap)
    r = run_simulation(p)
    quota = cap * r.n_units / 12
    cum = 0
    per_month = {}
    for e in r.events:      # capacity is used by subsidised unit/whole retrofits ...
        if e.kind != "shared" and e.subsidised:
            per_month[e.month] = per_month.get(e.month, 0) + 1
    for v in r.votes:       # ... and by shared measures
        per_month[v.month] = per_month.get(v.month, 0) + v.slots_used
    for m in range(p.horizon_months):
        cum += per_month.get(m, 0)
        assert per_month.get(m, 0) <= quota + 1
        assert cum <= quota * (m + 1) + 1 + 1e-9
    if cap == 0:
        assert r.adopted_units == 0


def test_monotone_in_deduction_rate():
    for mode_kw in ({}, {"credit_access": "open"}, {"refundable": True}):
        prev = -1
        for rate in [0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]:
            n = _final_adopted(replace(BASE, deduction_rate=rate, horizon_months=120, **mode_kw))
            assert n >= prev, (mode_kw, rate)
            prev = n


def test_monotone_adopted_sets_not_just_counts():
    lo = run_simulation(replace(BASE, deduction_rate=0.1))
    hi = run_simulation(replace(BASE, deduction_rate=0.5))
    assert {e.unit for e in lo.events} <= {e.unit for e in hi.events}


def test_zero_savings_world_gives_zero_adoption():
    r = run_simulation(replace(BASE, savings_scale=0.0, credit_access="none"))
    assert r.adopted_units == 0
    assert all(f["series"]["adopted_units"] == 0 for f in r.frames)


def test_means_test_restricts_eligibility():
    r = run_simulation(replace(BASE, delivery_mode="passthrough", means_test=True, means_test_max_quintile=2))
    assert r.adopted_units > 0
    for e in r.events:
        assert e.subsidised == (e.quintile <= 2)
        if not e.subsidised:        # outside the means test: market purchase, own financing, no public money
            assert e.state_pays_now == 0 and e.rebate == 0 and e.from_savings + e.loan == pytest.approx(e.price)


def test_params_validation():
    for bad in (dict(deduction_rate=1.5), dict(delivery_mode="x"), dict(credit_access="y"),
                dict(energy_scenario="z"), dict(horizon_months=0), dict(cost_per_m2=0)):
        with pytest.raises(ValueError):
            Params(**bad)


def test_frames_are_json_serialisable():
    import json
    r = run_simulation(replace(BASE, horizon_months=6))
    json.dumps(r.frames)
