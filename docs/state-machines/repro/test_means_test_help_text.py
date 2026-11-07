"""SM-4: pack.yaml tells the user the means test "Does not apply to the rebate"; model-spec.md 7.3, delivery.py:54 and runtime.js:153 apply it to the
rebate (an ineligible household buys on the market with no rebate). Same code in Python and JS, so this is a text-versus-behaviour defect, not drift.
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_means_test_help_text.py -q"""
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from retrofit_v3 import Params, run_simulation

ROOT = Path(__file__).resolve().parents[3]


def test_behaviour_means_test_also_restricts_the_rebate():          # passes today: pins what the code does
    p = Params(n_buildings=60, horizon_months=84, credit_access="open", deduction_rate=0.5, delivery_mode="rebate_market", means_test=True, means_test_max_quintile=2)
    r = run_simulation(replace(p, savings_scale=3.0))
    assert r.events and all((e.rebate > 0) <= (e.quintile <= 2) for e in r.events)
    assert any(e.quintile > 2 and not e.subsidised and e.rebate == 0 for e in r.events)


@pytest.mark.xfail(strict=True, reason="SM-4: user-facing help text contradicts the behaviour above")
def test_help_text_matches_behaviour():
    m = yaml.safe_load((ROOT / "packs/great-retrofit/pack.yaml").read_text())
    assert "Does not apply to the rebate" not in m["params"]["means_test"]["help"]
