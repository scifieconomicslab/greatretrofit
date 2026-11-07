"""SM-3 regression (issue #4): explicit buildings were not validated. A building with no units or zero total area crashed the run with a
ZeroDivisionError (frame: adopted_share = adopted / units; costs: shared_total * area / floor); an unknown tenure raised a bare KeyError; negative or NaN
areas ran silently. Params(buildings=...) now rejects them with a ValueError that names the building (same rules in JS: test_validation_vectors.py).
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest tests/model/test_degenerate_buildings.py -q"""
import pytest

from retrofit_v3 import Params, run_simulation
from retrofit_v3.entities import BuildingSpec


@pytest.mark.parametrize("spec", [BuildingSpec("x", "owner_occupied", ()), BuildingSpec("x", "condo", (0.0, 0.0)), BuildingSpec("x", "castle", (50.0,))],
                         ids=["zero-units", "zero-area", "bad-tenure"])
def test_degenerate_building_is_rejected_up_front(spec):
    with pytest.raises(ValueError, match=r"buildings\[0\] \('x'\)"):
        run_simulation(Params(buildings=(spec,), horizon_months=6))


@pytest.mark.parametrize("area", [-50.0, float("nan")])
def test_nonpositive_or_nan_area_is_rejected(area):
    with pytest.raises(ValueError, match=r"buildings\[0\] \('x'\)"):
        run_simulation(Params(buildings=(BuildingSpec("x", "owner_occupied", (area,)),), horizon_months=6))
