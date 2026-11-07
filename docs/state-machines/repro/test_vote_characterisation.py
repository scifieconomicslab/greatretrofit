"""Characterisation (these PASS today; they pin behaviour the doc calls out as reachable-but-questionable states, SM-5 and SM-6).
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_vote_characterisation.py -q -s"""
import fuzz_lib as F
from retrofit_v3.model import Simulation


def _runs():
    for s in range(200):
        c = F.case_for("manifest", s)
        c["params"].update(horizon_months=180, shared_measure=True)
        p = F.to_params(c["params"])
        sim = Simulation(p)
        for _ in range(p.horizon_months):
            sim.step()
        yield s, p, sim


def test_vote_can_be_stuck_pending_with_enough_support():
    """SM-5: floor-area support >= threshold but one owner cannot pay their share: the vote never passes, nothing in the frame says why except units_cannot_front."""
    stuck = [(s, b["id"], round(b["vote_yes_share"], 3), b["units_cannot_front"]) for s, p, sim in _runs() for b in sim.frame["buildings"]
             if b["shared_state"] == "pending" and b["vote_yes_share"] + 1e-9 >= p.vote_threshold]
    print(f"\nSM-5: {len(stuck)} buildings pending at t=180 with support >= threshold, e.g. (case, building, yes_share, units_cannot_front) = {stuck[:3]}")
    assert stuck


def test_shared_share_is_charged_after_the_payers_own_horizon():
    """SM-6: the vote charges every owner, including one whose expected stay has already ended (its NPV would be negative; the vote ignores NPV)."""
    late = [(s, e.unit, e.month, sim.units[e.unit].horizon) for s, p, sim in _runs() for e in sim.events if e.kind == "shared" and e.month >= sim.units[e.unit].horizon]
    print(f"\nSM-6: {len(late)} shared payments by households past their own horizon, e.g. (case, unit, month, horizon) = {late[:3]}")
    assert late
