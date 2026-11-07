"""SM-2 regression (issue #4): Params used to let NaN and +/-inf through (value <= 0 and value < 0 are False for NaN), and some of them reached the frames.
Now every number must be finite in both languages (shared vectors: test_validation_vectors.py).
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest tests/model/test_params_nonfinite.py -q"""
import math
from dataclasses import fields

import pytest

import fuzz_lib as F
from retrofit_v3 import Params, run_simulation

FLOATS = [f.name for f in fields(Params) if isinstance(f.default, float)]


@pytest.mark.parametrize("name", ["cost_per_m2", "discount_rate", "loan_rate", "canvass_target_hours", "waking_hours_per_week", "saving_per_m2_year"])
def test_nan_parameter_is_rejected(name):
    with pytest.raises(ValueError):
        Params(n_buildings=5, horizon_months=6, **{name: float("nan")})


@pytest.mark.parametrize("name", ["waking_hours_per_week", "saving_per_m2_year"])
def test_infinite_parameter_does_not_reach_frames(name):
    with pytest.raises(ValueError, match=name):      # rejected up front, so nothing non-finite can reach a frame (observed before: leisure_hours / canvass_hours / bills_saved)
        run_simulation(Params(n_buildings=15, horizon_months=36, **{name: float("inf")}))
    r = run_simulation(Params(n_buildings=15, horizon_months=36, **{name: 1e6}))
    assert not [p for fr in r.frames for p, v in F._walk_numbers(fr) if not math.isfinite(v)]
