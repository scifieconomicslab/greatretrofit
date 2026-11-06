"""Invariants for the mechanisms added after the audit: peer effect, shared-measure vote, canvassing time budget,
means test with market fallback, cost decomposition, conservation. They must hold whatever the economists answer."""
from dataclasses import replace

import pytest

from retrofit_v3 import Params, run_simulation
from retrofit_v3.entities import BuildingSpec
from retrofit_v3.model import Simulation
from retrofit_v3.scene_entities import SceneRules

# many small units per building, so condos are common
BASE = Params(n_buildings=40, horizon_months=84, scene_rules=SceneRules(avg_unit_area=60.0), keep_frames=True)
MODES = ["rebate_market", "passthrough", "public_service"]


def _run(**kw):
    return run_simulation(replace(BASE, **kw))


# ---- peer effect ----
@pytest.mark.parametrize("kw", [dict(delivery_mode="passthrough"), dict(credit_access="open"),
                                dict(delivery_mode="rebate_market", refundable=True)])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_peer_effect_never_reduces_adoption(kw, seed):
    """With common random numbers, a higher consideration chance can only add adopters (no shared vote, no queue)."""
    common = dict(seed=seed, shared_measure=False, canvass_target_hours=0.0, consider_prob_base=0.02, neighbour_boost=0.4, **kw)
    off, on = _run(peer_effect=False, **common), _run(peer_effect=True, **common)
    for f0, f1 in zip(off.frames, on.frames):
        assert f1["series"]["adopted_units"] >= f0["series"]["adopted_units"]
    assert {e.unit for e in off.events} <= {e.unit for e in on.events}
    assert on.adopted_units >= off.adopted_units


def test_peer_effect_acts_only_in_condos():
    kw = dict(shared_measure=False, canvass_target_hours=0.0, neighbour_boost=0.5, delivery_mode="passthrough")
    on, off = _run(peer_effect=True, **kw), _run(peer_effect=False, **kw)
    b_tenure = {b["id"]: b["tenure"] for b in on.frames[0]["buildings"]}
    assert any(t == "condo" for t in b_tenure.values())
    only_on = {e.unit for e in on.events} - {e.unit for e in off.events}
    assert only_on and all(b_tenure[e.building] == "condo" for e in on.events if e.unit in only_on)
    # owner-occupied units adopt identically
    assert [e for e in on.events if b_tenure[e.building] == "owner_occupied"] == [e for e in off.events if b_tenure[e.building] == "owner_occupied"]


# ---- shared-measure vote ----
@pytest.mark.parametrize("threshold", [0.5, 2.0 / 3.0, 0.9, 1.0])
@pytest.mark.parametrize("kw", [dict(delivery_mode="passthrough", consider_prob_base=0.02),
                                dict(credit_access="open", refundable=True, deduction_rate=0.5),
                                dict(delivery_mode="public_service", public_capacity=0.4)])
def test_vote_never_passes_below_threshold(threshold, kw):
    r = _run(vote_threshold=threshold, **kw)
    assert r.votes, "the case should exercise a vote"
    for v in r.votes:
        assert v.yes_share + 1e-9 >= threshold and v.threshold == threshold
    voted = {v.building: v.month for v in r.votes}
    assert len(voted) == len(r.votes)                      # at most one approval per building
    for e in r.events:                                     # no shared payment without a vote that month
        if e.kind == "shared":
            assert voted[e.building] == e.month
    for f in r.frames:                                     # approved buildings kept their support; pending ones show the vote not yet passed
        for b in f["buildings"]:
            if b["shared_state"] == "approved":
                assert b["vote_yes_share"] + 1e-9 >= threshold
            if b["shared_state"] == "none":
                assert b["vote_yes_share"] == 0


def test_higher_threshold_never_passes_earlier():
    kw = dict(delivery_mode="passthrough", consider_prob_base=0.02, seed=3)
    lo, hi = _run(vote_threshold=0.5, **kw), _run(vote_threshold=1.0, **kw)
    m_lo = {v.building: v.month for v in lo.votes}
    for v in hi.votes:
        assert v.building in m_lo and m_lo[v.building] <= v.month


def test_shared_cost_split_by_floor_area_and_completes_total():
    p = replace(BASE, delivery_mode="passthrough", seed=4)
    sim = Simulation(p)
    for _ in range(p.horizon_months):
        sim.step()
    assert sim.votes
    by_b = {}
    for e in sim.events:
        if e.kind == "shared":
            by_b.setdefault(e.building, []).append(e)
    area = {u.uid: u.area for u in sim.units}
    for bid, evs in by_b.items():
        b = next(b for b in sim.buildings if b.id == bid)
        assert len(evs) == b.units                                           # every owner pays
        ratios = [e.base_cost / area[e.unit] for e in evs]
        assert max(ratios) == pytest.approx(min(ratios))                     # same euros per m2: split by floor area
        assert sum(e.base_cost for e in evs) == pytest.approx(p.shared_share * p.cost_per_m2 * b.floor_area)


def test_shared_parts_exist_only_in_condos_with_two_units():
    r = _run(delivery_mode="passthrough")
    for b in r.frames[-1]["buildings"]:
        assert (b["shared_state"] != "none") == (b["tenure"] == "condo" and b["units"] >= 2)
    off = _run(delivery_mode="passthrough", shared_measure=False)
    assert all(b["shared_state"] == "none" for b in off.frames[-1]["buildings"]) and not off.votes
    assert all(e.kind == "whole" for e in off.events)


def test_shared_measure_blocked_when_an_owner_cannot_pay():
    r = _run(savings_scale=0.0, credit_access="none")      # nobody can finance anything under the rebate
    assert not r.votes and r.adopted_units == 0
    for e in _run(credit_access="income_tested").events:   # whoever paid a shared share could finance it
        assert e.from_savings + e.loan == pytest.approx(e.price)
        assert e.loan <= e.credit_limit + 1e-9


def test_single_unit_or_rental_buildings_have_no_vote():
    blds = (BuildingSpec("a", "owner_occupied", (100.0,)), BuildingSpec("r", "rental", (50.0, 50.0)), BuildingSpec("c", "condo", (70.0,)))
    r = run_simulation(Params(buildings=blds, horizon_months=24, delivery_mode="passthrough"))
    assert not r.votes and all(b["shared_state"] == "none" for b in r.final_frame["buildings"])


# ---- canvassing and the time budget ----
@pytest.mark.parametrize("work", [(42, 38, 36, 40, 48), (0, 0, 0, 0, 0), (200, 200, 200, 200, 200), (112, 60, 30, 60, 112)])
@pytest.mark.parametrize("target", [0.0, 2.0, 40.0])
def test_time_budget_never_negative(work, target):
    r = _run(work_hours_by_quintile=work, canvass_target_hours=target, delivery_mode="passthrough", horizon_months=36)
    free_cap = BASE.waking_hours_per_week * (1 + BASE.free_time_spread)
    for f in r.frames:
        s = f["series"]
        for k in range(5):
            assert s["leisure_hours_by_quintile"][k] >= 0 and s["canvass_hours_by_quintile"][k] >= 0
            assert s["canvass_hours_by_quintile"][k] <= min(target, free_cap) + 1e-9
    if work[0] == 200:       # no free time at all: nobody can canvass
        assert all(max(f["series"]["canvass_hours_by_quintile"]) == 0 for f in r.frames)


def test_free_hours_follow_working_hours_and_canvassing_spends_them():
    p = replace(BASE, work_hours_by_quintile=(60, 40, 40, 40, 20), delivery_mode="passthrough", free_time_spread=0.0)
    sim = Simulation(p)
    by_q = {}
    for u in sim.units:
        by_q.setdefault(u.quintile, set()).add(round(u.free_hours, 9))
    assert by_q[1] == {2.0} and by_q[2] == {22.0} and by_q[5] == {42.0}
    for _ in range(36):
        sim.step()
    for u in sim.units:
        assert 0 <= sim._spend(u) <= u.free_hours + 1e-12


def test_canvassing_only_in_co_owned_buildings_and_only_advocates():
    blds = tuple(BuildingSpec(f"h{i}", "owner_occupied", (100.0,)) for i in range(20))
    r = run_simulation(Params(buildings=blds, horizon_months=48, delivery_mode="passthrough"))
    assert r.adopted_units > 0
    assert all(max(f["series"]["canvass_hours_by_quintile"]) == 0 for f in r.frames)
    assert max(r.frames[0]["series"]["canvass_hours_by_quintile"]) == 0      # nobody advocates at t = 0


def test_canvassing_off_switch_and_pressure_help_follow():
    kw = dict(shared_measure=False, peer_effect=False, delivery_mode="passthrough", consider_prob_base=0.01, canvass_boost=0.5)
    off, on = _run(canvass_target_hours=0.0, **kw), _run(canvass_target_hours=6.0, **kw)
    assert on.adopted_units >= off.adopted_units


# ---- rebate, tax capacity, public capacity ----
@pytest.mark.parametrize("refundable", [False, True])
@pytest.mark.parametrize("kw", [dict(), dict(means_test=True), dict(credit_access="open", shared_share=0.7)])
def test_rebate_never_above_tax_payable_or_cost_even_across_parts(refundable, kw):
    p = replace(BASE, refundable=refundable, deduction_rate=0.9, **kw)
    sim = Simulation(p)
    for _ in range(p.horizon_months):
        sim.step()
    tax = {u.uid: u.tax for u in sim.units}
    total = {}
    for e in sim.events:
        assert e.rebate <= e.price + 1e-9
        total[e.unit] = total.get(e.unit, 0.0) + e.rebate
        if not refundable:
            assert e.rebate <= e.tax_payable + 1e-9
    if not refundable:      # one year's tax capacity serves all of a household's payments together
        for uid, r in total.items():
            assert r <= tax[uid] + 1e-9


def test_means_test_applies_to_rebate_too():
    r = _run(means_test=True, means_test_max_quintile=2, credit_access="open", deduction_rate=0.5, refundable=True)
    assert any(e.rebate > 0 for e in r.events)
    for e in r.events:
        assert (e.rebate > 0) <= (e.quintile <= 2)
        assert e.subsidised == (e.quintile <= 2)


@pytest.mark.parametrize("cap", [0.0, 0.05, 0.4])
def test_public_capacity_includes_shared_work(cap):
    r = _run(delivery_mode="public_service", public_capacity=cap)
    quota = cap * r.n_units / 12
    used = {}
    for e in r.events:
        if e.kind != "shared" and e.subsidised:
            used[e.month] = used.get(e.month, 0) + 1
    for v in r.votes:
        used[v.month] = used.get(v.month, 0) + v.slots_used
    cum = 0
    for m in range(BASE.horizon_months):
        cum += used.get(m, 0)
        assert cum <= quota * (m + 1) + 1 + 1e-9
    if cap == 0:
        assert not r.votes and r.adopted_units == 0


# ---- conservation and decomposition ----
@pytest.mark.parametrize("mode", MODES)
def test_unit_counts_conserved(mode):
    r = _run(delivery_mode=mode)
    n_units = sum(b["units"] for b in r.frames[0]["buildings"])
    assert n_units == r.n_units
    for f in r.frames:
        assert sum(b["units"] for b in f["buildings"]) == n_units
        done = sum(round(b["adopted_share"] * b["units"]) for b in f["buildings"])
        assert done == f["series"]["adopted_units"] <= n_units
        assert sum(f["series"]["state_counts"].values()) == len(f["buildings"])
        assert sum(f["series"]["shared_counts"].values()) == sum(b["shared_state"] != "none" for b in f["buildings"])
    # each unit pays at most one own part and one shared part
    per = {}
    for e in r.events:
        per.setdefault(e.unit, []).append(e.kind)
    for kinds in per.values():
        assert sorted(kinds) in (["whole"], ["unit"], ["shared"], ["shared", "unit"])
    completed = sum(1 for k in per.values() if "whole" in k or sorted(k) == ["shared", "unit"])
    assert completed == r.adopted_units


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("kw", [dict(), dict(means_test=True, credit_access="open")])
def test_cost_per_retrofit_is_sum_of_components(mode, kw):
    r = _run(delivery_mode=mode, **kw)
    seen = False
    for f in r.frames:
        s = f["series"]
        if s["cost_per_retrofit"] is None:
            assert s["cost_per_retrofit_parts"] is None
            continue
        seen = True
        parts = s["cost_per_retrofit_parts"]
        assert parts["base"] + parts["markup"] == pytest.approx(s["cost_per_retrofit"], rel=1e-12)
        assert parts["base"] > 0 and parts["markup"] >= 0
    assert seen
    p = r.params
    for e in r.events:      # each payment: price = base x (1 + margin or overhead)
        rate = p.public_overhead if (mode == "public_service" and e.subsidised) else p.vendor_margin
        assert e.price == pytest.approx(e.base_cost * (1.0 + rate))


def test_household_cash_timeline_consistent_with_bills_when_state_pays():
    p = replace(BASE, delivery_mode="passthrough")
    sim = Simulation(p)
    for _ in range(p.horizon_months):
        sim.step()
    assert sum(u.cash_net for u in sim.units) == pytest.approx(sim.bills_saved)     # no outlay, no loans, no rebate
    s = sim.frame["series"]["net_cash_by_quintile"]
    assert all(x is None or x >= 0 for x in s)


def test_household_cash_rebate_mode_pays_out_then_recoups():
    r = _run(credit_access="open", deduction_rate=0.5, refundable=True, horizon_months=120)
    assert any(x is not None for x in r.frames[-1]["series"]["net_cash_by_quintile"])
    first = next(f for f in r.frames if any(x is not None for x in f["series"]["net_cash_by_quintile"]))
    assert min(x for x in first["series"]["net_cash_by_quintile"] if x is not None) < 0     # they paid before they got anything back


def test_new_param_validation():
    for bad in (dict(vote_threshold=0.0), dict(vote_threshold=1.5), dict(shared_share=1.5), dict(work_hours_by_quintile=(1, 2, 3)),
                dict(work_hours_by_quintile=(1, 2, 3, 4, -1)), dict(canvass_saturation_hours=0), dict(canvass_boost=2),
                dict(loan_rate_risk_premium=-0.1), dict(canvass_target_hours=-1)):
        with pytest.raises(ValueError):
            Params(**bad)


def test_loan_rate_premium_raises_cost_for_low_income_borrowers_only():
    p = replace(BASE, credit_access="open", loan_rate_risk_premium=0.05)
    sim = Simulation(p)
    lo = next(u for u in sim.units if u.income < p.credit_income_threshold)
    hi = next(u for u in sim.units if u.income >= p.credit_income_threshold)
    assert sim._loan_rate(lo) == pytest.approx(p.loan_rate + 0.05) and sim._loan_rate(hi) == p.loan_rate
