"""Fuzz helpers for the v3 model: random parameter/scene generator and the frame/event/state invariants.

Used by test_fuzz_python.py, test_fuzz_parity.py, test_fuzz_js_lifecycle.py and by docs/state-machines/repro/*.
Every generated case is a plain JSON-serialisable dict so the same case runs in Python and in JavaScript:
    {"seed": <case seed>, "params": {...Params fields...}, "kind": "manifest" | "edge"}
`params["buildings"]` (optional) is a list of {id, tenure, unit_areas, rental_draw}.
Cite failures by (kind, case seed): ``case_for(kind, seed)`` rebuilds the case exactly.
"""
from __future__ import annotations

import math
import random
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "v3" / "src"))

from retrofit_v3 import Params  # noqa: E402
from retrofit_v3.entities import BuildingSpec  # noqa: E402
from retrofit_v3.model import Simulation  # noqa: E402

TOL = 1e-6          # money tolerance (euros); float sums in different orders differ far less than this


def to_params(d: dict) -> Params:
    d = dict(d)
    b = d.pop("buildings", None)
    if b:
        d["buildings"] = tuple(BuildingSpec(x["id"], x["tenure"], tuple(x["unit_areas"]), x.get("rental_draw")) for x in b)
    return Params(**d)


# ---------------------------------------------------------------- generators
def _scene(r: random.Random, mode: str):
    """Explicit buildings: includes all-rental, single building, one unit, big condos, uneven areas."""
    kind = r.choice(["all_rental", "single", "one_unit_each", "big_condo", "mixed", "mixed"] if mode == "edge" else ["mixed"])
    n = {"all_rental": r.randint(1, 6), "single": 1, "one_unit_each": r.randint(2, 8), "big_condo": r.randint(1, 3), "mixed": r.randint(2, 10)}[kind]
    out = []
    for i in range(n):
        if kind == "all_rental":
            tenure, nu = "rental", r.randint(1, 4)
        elif kind == "one_unit_each":
            tenure, nu = "owner_occupied", 1
        elif kind == "big_condo":
            tenure, nu = "condo", r.randint(15, 40)
        else:
            nu = r.choice([1, 1, 2, 3, 4, 6, 8])
            tenure = "rental" if r.random() < 0.2 else ("owner_occupied" if nu == 1 else "condo")
        areas = [round(r.uniform(15, 250) if mode == "edge" else r.uniform(40, 120), 3) for _ in range(nu)]
        out.append({"id": f"f{i}", "tenure": tenure, "unit_areas": areas, "rental_draw": None})
    return out


def manifest_params(r: random.Random) -> dict:
    """Parameters the shell can set: pack.yaml ranges, lag >= 1 (lag 0 is its own repro)."""
    return {
        "deduction_rate": r.choice([0.0, 1.0, round(r.random(), 2)]),
        "refundable": r.random() < 0.5,
        "rebate_lag_months": r.choice([1, 12, 24, r.randint(1, 24)]),
        "credit_access": r.choice(["income_tested", "open", "none"]),
        "loan_rate": r.choice([0.0, 0.08, round(r.uniform(0, 0.08), 3)]),
        "delivery_mode": r.choice(["rebate_market", "passthrough", "public_service"]),
        "vendor_margin": r.choice([0.0, 0.4, round(r.uniform(0, 0.4), 2)]),
        "public_overhead": r.choice([0.0, 0.4, round(r.uniform(0, 0.4), 2)]),
        "public_capacity": r.choice([0.0, 1.0, 0.01, round(r.random(), 2)]),
        "means_test": r.random() < 0.4,
        "energy_scenario": r.choice(["flat", "rising", "shock"]),
        "peer_effect": r.random() < 0.5,
        "shared_measure": r.random() < 0.7,
        "vote_threshold": r.choice([0.5, 1.0, round(r.uniform(0.5, 1.0), 2)]),
        "rental_share_single": r.choice([0.0, 1.0, round(r.random(), 2)]),
        "rental_share_multi": r.choice([0.0, 1.0, round(r.random(), 2)]),
        "canvass_target_hours": r.choice([0.0, 10.0, round(r.uniform(0, 10), 1)]),
    }


def edge_extras(r: random.Random) -> dict:
    """Non-manifest levers at their extremes (reachable through the Python API and by editing DEFAULTS)."""
    pick = lambda name, opts: {name: r.choice(opts)} if r.random() < 0.35 else {}   # noqa: E731
    d = {}
    d.update(pick("vote_threshold", [0.01, 1.0]))
    d.update(pick("shared_share", [0.0, 1.0, 0.5]))
    d.update(pick("consider_prob_base", [0.0, 1.0, 0.5]))
    d.update(pick("neighbour_boost", [0.0, 1.0]))
    d.update(pick("canvass_boost", [0.0, 1.0]))
    d.update(pick("discount_rate", [0.0, 1.0, 0.3]))
    d.update(pick("tax_rate", [0.0, 1.0]))
    d.update(pick("savings_scale", [0.0, 50.0]))
    d.update(pick("savings_usable_share", [0.0, 1.0]))
    d.update(pick("loan_term_months", [1, 1200]))
    d.update(pick("cost_per_m2", [1e-6, 1e5]))
    d.update(pick("saving_per_m2_year", [1e-6, 1e5]))
    d.update(pick("credit_loan_to_income", [0.0, 100.0]))
    d.update(pick("credit_income_threshold", [0.0, 1e9]))
    d.update(pick("free_time_spread", [0.0, 1.0]))
    d.update(pick("canvass_saturation_hours", [1e-6, 1e6]))
    d.update(pick("means_test_max_quintile", [1, 5]))
    d.update(pick("years_in_dwelling_min", [0.01, 40.0]))
    return d


def case_for(kind: str, seed: int) -> dict:
    r = random.Random(f"{kind}:{seed}")
    p = manifest_params(r)
    if kind == "edge":
        p.update(edge_extras(r))
        if p.get("years_in_dwelling_min", 5.0) > 25.0:
            p["years_in_dwelling_max"] = 60.0
    p["seed"] = r.randint(0, 2 ** 31 - 1)
    p["scene_seed"] = r.randint(0, 2 ** 31 - 1)
    if kind == "edge" and r.random() < 0.3:        # seeds beyond int32: the adapter does seed|0, Python masks to 32 bits
        p["seed"] = r.choice([2 ** 31, 3_000_000_000, 2 ** 32 - 1, 2 ** 32 + 5, 2 ** 40 + 7])
    p["horizon_months"] = r.choice([6, 24, 36, 60])
    if r.random() < 0.5 or kind == "edge" and r.random() < 0.7:
        p["buildings"] = _scene(r, kind)
    else:
        p["n_buildings"] = r.choice([1, 2, 5, 12, 25])
    return {"kind": kind, "seed": seed, "params": p}


# ---------------------------------------------------------------- invariants
def _walk_numbers(x, path=""):
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return
    if isinstance(x, (int, float)):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _walk_numbers(v, f"{path}.{k}")
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from _walk_numbers(v, f"{path}[{i}]")


def frame_problems(f, prev, n_buildings, n_units_total, modelled_units) -> list[str]:
    """Invariants of one frame (see docs/state-machines.md, section 'Frame invariants')."""
    bad = []
    s = f["series"]
    for path, v in _walk_numbers(f):
        if not math.isfinite(v):
            bad.append(f"non-finite number at {path}: {v}")
    if f["schema"] != 1:
        bad.append("schema")
    if abs(f["year"] - f["t"] / 12.0) > 1e-12:
        bad.append("year != t/12")
    if len(f["buildings"]) != n_buildings:
        bad.append(f"frame has {len(f['buildings'])} buildings, scene has {n_buildings}")
    counts = {"not_retrofitted": 0, "partial": 0, "retrofitted": 0, "not_modelled": 0}
    shared = {"pending": 0, "approved": 0}
    adopted = 0.0
    for b in f["buildings"]:
        u, a = b["units"], b["adopted_share"]
        counts[b["state"]] = counts.get(b["state"], 0) + 1
        done = a * u
        adopted += done
        if u < 1:
            bad.append(f"{b['id']}: units {u}")
        if not (0.0 <= a <= 1.0):
            bad.append(f"{b['id']}: adopted_share {a}")
        if abs(done - round(done)) > 1e-6:
            bad.append(f"{b['id']}: adopted_share*units not an integer ({done})")
        if b["tenure"] == "rental":
            if b["state"] != "not_modelled" or a != 0 or b["shared_state"] != "none" or b["units_cannot_front"] != 0:
                bad.append(f"{b['id']}: rental building not inert")
        else:
            want = "not_retrofitted" if round(done) == 0 else ("retrofitted" if round(done) == u else "partial")
            if b["state"] != want:
                bad.append(f"{b['id']}: state {b['state']} but {round(done)}/{u} units done")
        if not (0 <= b["units_cannot_front"] <= u - round(done)):
            bad.append(f"{b['id']}: units_cannot_front {b['units_cannot_front']} of {u - round(done)} left")
        if not (1.0 <= b["income_q_mean"] <= 5.0):
            bad.append(f"{b['id']}: income_q_mean {b['income_q_mean']}")
        if not (0.0 <= b["vote_yes_share"] <= 1.0):
            bad.append(f"{b['id']}: vote_yes_share {b['vote_yes_share']}")
        if b["shared_state"] == "none" and b["vote_yes_share"] != 0:
            bad.append(f"{b['id']}: vote share without shared parts")
        if b["shared_state"] == "approved":
            shared["approved"] += 1
        elif b["shared_state"] == "pending":
            shared["pending"] += 1
        if prev is not None:
            pb = prev["buildings"][f["buildings"].index(b)]
            if b["adopted_share"] < pb["adopted_share"] - 1e-12:
                bad.append(f"{b['id']}: adopted_share fell")
            if pb["shared_state"] == "approved" and b["shared_state"] != "approved":
                bad.append(f"{b['id']}: approval withdrawn")
    if counts != s["state_counts"]:
        bad.append(f"state_counts {s['state_counts']} != recount {counts}")
    if sum(s["state_counts"].values()) != n_buildings:
        bad.append("state_counts do not sum to the number of buildings")
    if shared != s["shared_counts"]:
        bad.append("shared_counts mismatch")
    if sum(s["tenure_counts"].values()) != n_buildings:
        bad.append("tenure_counts do not sum")
    if s["adopted_units"] != round(adopted):
        bad.append(f"adopted_units {s['adopted_units']} != sum over buildings {adopted}")
    if s["adopted_units"] > modelled_units:
        bad.append("more units adopted than units in modelled buildings")
    for name in ("adoption_by_quintile", "rebate_per_euro", "can_front_cost", "canvass_hours_by_quintile", "leisure_hours_by_quintile", "net_cash_by_quintile"):
        if len(s[name]) != 5:
            bad.append(f"{name} has {len(s[name])} values")
    for k in range(5):
        for name in ("adoption_by_quintile", "can_front_cost"):
            v = s[name][k]
            if v is not None and not (0.0 <= v <= 1.0 + 1e-12):
                bad.append(f"{name}[{k}] = {v}")
        v = s["rebate_per_euro"][k]
        if v is not None and not (-1e-12 <= v <= 1.0 + 1e-9):
            bad.append(f"rebate_per_euro[{k}] = {v}")
        if s["canvass_hours_by_quintile"][k] < -1e-12 or s["leisure_hours_by_quintile"][k] < -1e-12:
            bad.append(f"negative hours in quintile {k}")
    n = s["adopted_units"]
    if (s["cost_per_retrofit"] is None) != (n == 0) or (s["cost_per_retrofit_parts"] is None) != (n == 0):
        bad.append("cost_per_retrofit null-ness does not follow adopted_units == 0")
    elif n:
        parts = s["cost_per_retrofit_parts"]
        if abs(parts["base"] + parts["markup"] - s["cost_per_retrofit"]) > TOL * max(1.0, s["cost_per_retrofit"]) * 1e-3:
            bad.append(f"cost parts {parts} do not sum to cost_per_retrofit {s['cost_per_retrofit']}")
        if parts["markup"] < -1e-9 or parts["base"] < 0:
            bad.append(f"negative cost part {parts}")
    if s["public_cost"] < -1e-9 or s["bills_saved"] < -1e-9:
        bad.append("negative cumulative money series")
    if prev is not None:
        ps = prev["series"]
        for name in ("public_cost", "bills_saved", "adopted_units"):
            if s[name] < ps[name] - 1e-9:
                bad.append(f"{name} decreased {ps[name]} -> {s[name]}")
    return bad


def sim_problems(sim: Simulation) -> list[str]:
    """White-box invariants of the live Simulation state (units, queues, counters)."""
    bad, p = [], sim.p
    for u in sim.units:
        if u.savings < -1e-9:
            bad.append(f"unit {u.uid}: negative savings {u.savings}")
        if u.tax_left < -1e-12 or u.tax_left > u.tax + 1e-9:
            bad.append(f"unit {u.uid}: tax_left {u.tax_left} outside [0, {u.tax}]")
        if u.complete and not (u.unit_done and (u.shared_paid or not u.needs_shared)):
            bad.append(f"unit {u.uid}: complete without both parts")
        if not u.complete and u.unit_done and (u.shared_paid or not u.needs_shared):
            bad.append(f"unit {u.uid}: both parts paid but not complete")
        if u.shared_paid and not u.needs_shared:
            bad.append(f"unit {u.uid}: shared part paid in a building without shared parts")
        if u.complete and sim.buildings[u.bidx].tenure == "rental":
            bad.append(f"unit {u.uid}: adopted in a rental building")
    for bi in range(len(sim.buildings)):
        if sim.adopted_in_b[bi] != sum(1 for i in sim.by_b[bi] if sim.units[i].complete):
            bad.append(f"building {bi}: adopted_in_b out of step with units")
        if sim.adopted_in_b[bi] > sim.buildings[bi].units:
            bad.append(f"building {bi}: adopted beyond units")
        if sim.approved[bi] and not all(sim.units[i].shared_paid for i in sim.by_b[bi]):
            bad.append(f"building {bi}: approved but an owner has not paid the shared part")
        if not sim.approved[bi] and any(sim.units[i].shared_paid for i in sim.by_b[bi]):
            bad.append(f"building {bi}: shared part paid without approval")
    if sim.n_complete != sum(1 for u in sim.units if u.complete) or sim.n_complete != sum(sim.adopted_in_b):
        bad.append("n_complete out of step")
    if sum(sim.q_adopt) != sim.n_complete:
        bad.append("q_adopt out of step")
    for month, items in sim.pending.items():
        if month < sim.t:
            bad.append(f"rebate queue holds {len(items)} item(s) due in month {month}, already past (t={sim.t}): never delivered")
        for uid, amount in items:
            if not (0 <= uid < len(sim.units)) or amount <= 0:
                bad.append(f"bad rebate queue item {uid} {amount}")
    if not (0.0 <= sim.carry < 1.0 + 1e-12):
        bad.append(f"public service carry {sim.carry}")
    return bad


def event_problems(res, p: Params) -> list[str]:
    """Invariants over the event log: cost, finance, rebate, capacity, conservation of money flows."""
    bad = []
    seen = set()
    n_units = res.n_units
    quota = p.public_capacity * n_units / 12.0
    used = {}
    for e in res.events:
        key = (e.unit, e.kind)
        if key in seen:
            bad.append(f"unit {e.unit} paid kind {e.kind} twice")
        seen.add(key)
        if e.price < 0 or e.base_cost < 0 or e.price + 1e-9 < e.base_cost:
            bad.append(f"event {e}: price below base cost")
        if abs(e.from_savings + e.loan + e.state_pays_now - e.price) > TOL * max(1.0, e.price) * 1e-3:
            bad.append(f"event {e}: payers do not add up to the price")
        if e.from_savings < -1e-9 or e.loan < -1e-9 or e.from_savings > e.savings_at_adoption + 1e-9:
            bad.append(f"event {e}: savings overdrawn")
        if e.loan > e.credit_limit + 1e-6:
            bad.append(f"event {e}: loan above credit limit")
        if e.rebate < -1e-12 or e.rebate > e.price + 1e-9:
            bad.append(f"event {e}: rebate above cost")
        if not p.refundable and e.rebate > e.tax_payable + 1e-9:
            bad.append(f"event {e}: rebate above tax payable")
        if e.rebate > 0 and e.rebate_lag_months != p.rebate_lag_months:
            bad.append(f"event {e}: lag")
        if p.delivery_mode == "public_service" and e.subsidised and e.kind != "shared":
            used[e.month] = used.get(e.month, 0) + 1
        if p.means_test and e.subsidised and e.quintile > p.means_test_max_quintile:
            bad.append(f"event {e}: subsidy outside the means test")
    for v in res.votes:
        used[v.month] = used.get(v.month, 0) + v.slots_used
        if v.yes_share + 1e-9 < v.threshold:
            bad.append(f"vote {v}: passed below threshold")
    if p.delivery_mode == "public_service":
        carry = 0.0
        for m in range(p.horizon_months):
            slots = int(quota + carry)
            carry = quota + carry - slots
            if used.get(m, 0) > slots:
                bad.append(f"month {m}: public service completed {used[m]} jobs with {slots} slots")
    # money conservation: public_cost = vendor payments + rebates that arrived (arrival month <= last executed step)
    T = len(res.frames) - 1 if res.frames else p.horizon_months
    want = 0.0
    for e in res.events:
        want += e.state_pays_now
        if e.rebate and e.month + e.rebate_lag_months <= T - 1:
            want += e.rebate
    got = res.final_frame["series"]["public_cost"]
    if abs(got - want) > TOL * max(1.0, want) * 1e-3:
        bad.append(f"public_cost {got} != payments + arrived rebates {want}")
    return bad


def run_checked(case: dict, check_sim_every_step: bool = True) -> tuple[list[str], object]:
    """Run a case step by step on Simulation; returns (problems, result-like). Problems are prefixed with the step."""
    from retrofit_v3.results import Result
    p = to_params(case["params"])
    sim = Simulation(p)
    n_b = len(sim.buildings)
    modelled = sum(b.units for b in sim.buildings if b.tenure != "rental")
    frames, bad = [sim.frame], []
    bad += [f"t=0: {x}" for x in frame_problems(sim.frame, None, n_b, len(sim.units), modelled)]
    prev = sim.frame
    for _ in range(p.horizon_months):
        f = sim.step()
        frames.append(f)
        bad += [f"t={f['t']}: {x}" for x in frame_problems(f, prev, n_b, len(sim.units), modelled)]
        if check_sim_every_step:
            bad += [f"t={f['t']}: {x}" for x in sim_problems(sim)]
        prev = f
        if len(bad) > 12:
            break
    res = Result(p, frames, tuple(sim.events), tuple(sim.votes), sim.frame, len(sim.units), len(sim.buildings))
    bad += event_problems(res, p)
    return bad, res
