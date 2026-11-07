"""Issue #3 (SM-7, SM-8, SM-9): the scene/runtime contract, in both languages.

JS: scene_contract.js runs the pack the way the page does (paperdolls packruntime.js, read-only). Python: the same id rule and dwelling cap in scene_entities.py;
the golden scene_tables cases (packs/great-retrofit/tests) check that both give the same buildings, ids and capped list.
"""
import math
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from retrofit_v3.scene_entities import MAX_UNITS_PER_BUILDING, build_entities, scene_key

HERE = Path(__file__).resolve().parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_js_scene_contract():
    r = subprocess.run(["node", str(HERE / "scene_contract.js")], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("ok  ") >= 5 or "skip" in r.stdout


def test_id_rule_hash_index():
    assert scene_key(None, 5) == "#5" and scene_key(0, 3) == "0" and scene_key("", 1) == "" and scene_key(7, 0) == "7"
    rows = [{"area": 140.0, "storeys": 2, "residential": True}, {"id": None, "area": 90.0, "storeys": 1, "residential": True},
            {"id": "shop", "area": 50.0, "storeys": 1, "residential": False}, {"id": 7, "area": 300.0, "storeys": 3, "residential": True}]
    e = build_entities(rows)
    assert e.scene_ids == ("#0", "#1", "7")
    assert e.excluded == (("shop", "non_residential"),)


def test_dwelling_cap_keeps_floor_area_and_reports_and_warns():
    rows = [{"id": "huge", "area": 5000.0, "storeys": 800, "residential": True}, {"id": "ok", "area": 200.0, "storeys": 3, "residential": True}]
    with pytest.warns(UserWarning, match="huge with 40000"):
        e = build_entities(rows)
    assert e.capped == (("huge", 40000),)
    assert e.buildings[0].units == MAX_UNITS_PER_BUILDING == 1000
    assert e.buildings[0].floor_area == pytest.approx(5000 * 800 * 0.8)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert build_entities(rows[1:]).capped == ()


@pytest.mark.parametrize("area,storeys", [(math.inf, 2), (math.nan, 2), (1e308, 10 ** 10), (-5.0, 2), (0.0, 2), (100.0, -1)])
def test_invalid_geometry_is_excluded_not_a_crash(area, storeys):
    e = build_entities([{"id": "a", "area": area, "storeys": storeys, "residential": True}])
    assert e.buildings == () and e.excluded == (("a", "invalid_geometry"),)
