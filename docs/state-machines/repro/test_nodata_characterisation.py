"""SM-15 (characterisation, PASSES today): quintiles with no household are drawn as 0, not as no-data, in the per-quintile series that are not nullable.
With fewer than 5 dwellings some quintiles are empty (model.py:246: quintile = 1 + rank*5//n). The shell shows 0 leisure hours / 0 adoption for them.
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_nodata_characterisation.py -q -s"""
from retrofit_v3 import Params, run_simulation
from retrofit_v3.entities import BuildingSpec


def test_empty_quintiles_read_as_zero_not_no_data():
    r = run_simulation(Params(buildings=(BuildingSpec("a", "owner_occupied", (80.0,)), BuildingSpec("b", "owner_occupied", (90.0,))), horizon_months=12))
    s = r.final_frame["series"]
    print("\nadoption_by_quintile  ", s["adoption_by_quintile"])
    print("leisure_hours_by_quintile", s["leisure_hours_by_quintile"])
    print("can_front_cost         ", s["can_front_cost"], "<- the nullable series does say no data")
    assert s["leisure_hours_by_quintile"][4] == 0.0 and s["adoption_by_quintile"][4] == 0.0 and s["can_front_cost"][4] is None
