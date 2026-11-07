"""SM-3: BuildingSpec / Params do not validate explicit buildings. A building with no units or zero total area crashes the run with a
ZeroDivisionError (frame: adopted_share = adopted / units; costs: shared_total * area / floor); an unknown tenure raises a bare KeyError.
Not reachable through bind.js (buildEntities makes >= 1 unit and area > 0) but reachable through Params(buildings=...) and `ents.building.specs`.
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_degenerate_buildings.py -q"""
import pytest

from retrofit_v3 import Params, run_simulation
from retrofit_v3.entities import BuildingSpec


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SM-3: ZeroDivisionError escapes instead of a ValueError naming the building")
@pytest.mark.parametrize("spec", [BuildingSpec("x", "owner_occupied", ()), BuildingSpec("x", "condo", (0.0, 0.0)), BuildingSpec("x", "castle", (50.0,))],
                         ids=["zero-units", "zero-area", "bad-tenure"])
def test_degenerate_building_is_rejected_up_front(spec):
    try:
        run_simulation(Params(buildings=(spec,), horizon_months=6))
    except ValueError:
        return
    except Exception as e:          # noqa: BLE001
        raise AssertionError(f"{type(e).__name__}: {e}") from e
    raise AssertionError("accepted")


@pytest.mark.xfail(strict=True, reason="SM-3: negative and NaN unit areas run silently (units_cannot_front counts the NaN unit as unable to pay)")
@pytest.mark.parametrize("area", [-50.0, float("nan")])
def test_nonpositive_or_nan_area_is_rejected(area):
    with pytest.raises(ValueError):
        run_simulation(Params(buildings=(BuildingSpec("x", "owner_occupied", (area,)),), horizon_months=6))
