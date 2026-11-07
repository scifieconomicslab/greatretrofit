"""SM-2: Params validation lets NaN and +/-inf through (value <= 0 and value < 0 are False for NaN), and some of them reach the frames.
Not reachable from the shell sliders (pack.yaml ranges are finite); reachable from the Python API and from any future manifest entry without min/max.
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_params_nonfinite.py -q"""
import math
from dataclasses import fields

import pytest

import fuzz_lib as F
from retrofit_v3 import Params, run_simulation

FLOATS = [f.name for f in fields(Params) if isinstance(f.default, float)]


@pytest.mark.xfail(strict=True, reason="SM-2: validate_positive/nonnegative accept NaN and inf")
@pytest.mark.parametrize("name", ["cost_per_m2", "discount_rate", "loan_rate", "canvass_target_hours", "waking_hours_per_week", "saving_per_m2_year"])
def test_nan_parameter_is_rejected(name):
    with pytest.raises(ValueError):
        Params(n_buildings=5, horizon_months=6, **{name: float("nan")})


@pytest.mark.xfail(strict=True, reason="SM-2: an infinite parameter is accepted and puts inf in the frames")
@pytest.mark.parametrize("name", ["waking_hours_per_week", "saving_per_m2_year"])
def test_infinite_parameter_does_not_reach_frames(name):
    r = run_simulation(Params(n_buildings=15, horizon_months=36, **{name: float("inf")}))
    bad = [p for fr in r.frames for p, v in F._walk_numbers(fr) if not math.isfinite(v)]
    assert not bad, f"non-finite numbers in frames, e.g. {bad[:2]}"      # observed: leisure_hours / canvass_hours / bills_saved
