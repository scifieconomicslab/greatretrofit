"""scene_entities on a small synthetic table (no paperdolls dependency)."""
import pytest

from retrofit_v3.scene_entities import SceneRules, build_entities

ROWS = [
    {"id": "a", "area": 90, "storeys": 1, "residential": True},
    {"id": "b", "area": 200, "storeys": 5, "residential": True},
    {"id": "c", "area": 500, "storeys": 2, "residential": False},
    {"id": "d", "area": 0, "storeys": 2, "residential": True},
    {"id": "e", "area": 120, "storeys": 3, "residential": True},
]
NO_RENTAL = SceneRules(rental_share_single=0.0, rental_share_multi=0.0)


def test_units_tenure_and_exclusions():
    out = build_entities(ROWS, NO_RENTAL, scene_seed=1)
    assert out.scene_ids == ("a", "b", "e")
    assert dict(out.excluded) == {"c": "non_residential", "d": "invalid_geometry"}
    by = {b.id: b for b in out.buildings}
    assert by["a"].units == 1 and by["a"].tenure == "owner_occupied"
    assert by["b"].units == round(200 * 5 * 0.8 / 80) == 10 and by["b"].tenure == "condo"
    assert by["b"].floor_area == pytest.approx(200 * 5 * 0.8)
    assert all(a > 0 for b in out.buildings for a in b.unit_areas)


def test_deterministic_and_scene_seed_only():
    assert build_entities(ROWS, scene_seed=3) == build_entities(ROWS, scene_seed=3)


def test_all_rental_when_share_one():
    out = build_entities(ROWS, SceneRules(rental_share_single=1.0, rental_share_multi=1.0))
    assert {b.tenure for b in out.buildings} == {"rental"}
