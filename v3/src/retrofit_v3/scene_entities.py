"""Scene table -> model buildings and units (model-from-scene, plan D3).

Input rows: dicts with id, area (footprint m2), storeys, residential (bool).
All rules and numbers are PLACEHOLDERS (see v3/docs/placeholders.md). Randomness
uses hash_uniform keyed by a *scene seed* separate from the model seed.
Does not depend on paperdolls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Tuple

from .common.rng import Rng, hash_uniform
from .entities import BuildingSpec
from .common.validation import validate_positive, validate_probability


@dataclass(frozen=True)
class SceneRules:
    usable_fraction: float = 0.8        # PLACEHOLDER share of gross area that is dwelling floor
    avg_unit_area: float = 80.0         # PLACEHOLDER m2 per dwelling unit
    rental_share_single: float = 0.10   # PLACEHOLDER share of single-unit buildings that are rented
    rental_share_multi: float = 0.30    # PLACEHOLDER share of multi-unit buildings that are rental
    unit_area_spread: float = 0.2       # PLACEHOLDER +/- relative spread of unit sizes in a building

    def __post_init__(self):
        validate_probability(self.usable_fraction, "usable_fraction")
        validate_positive(self.avg_unit_area, "avg_unit_area")
        validate_probability(self.rental_share_single, "rental_share_single")
        validate_probability(self.rental_share_multi, "rental_share_multi")
        validate_probability(self.unit_area_spread, "unit_area_spread")


@dataclass(frozen=True)
class SceneEntities:
    buildings: Tuple[BuildingSpec, ...]
    excluded: Tuple[Tuple[str, str], ...]          # (scene id, reason)
    scene_ids: Tuple[str, ...]                     # model building index -> scene id


def build_entities(rows: Iterable[Mapping], rules: SceneRules = SceneRules(), scene_seed: int = 0) -> SceneEntities:
    buildings, excluded = [], []
    for k, row in enumerate(rows):
        sid = str(row["id"])
        if not row.get("residential", False):
            excluded.append((sid, "non_residential"))
            continue
        area, storeys = float(row["area"]), int(row.get("storeys") or 1)
        if area <= 0 or storeys <= 0:
            excluded.append((sid, "invalid_geometry"))
            continue
        gross = area * storeys * rules.usable_fraction
        n_units = max(1, round(gross / rules.avg_unit_area))
        rental_share = rules.rental_share_single if n_units == 1 else rules.rental_share_multi
        draw = hash_uniform(scene_seed, k, 1)
        if draw < rental_share:
            tenure = "rental"
        else:
            tenure = "owner_occupied" if n_units == 1 else "condo"
        # split gross area over units with a deterministic spread, preserving the total
        rng = Rng(int(hash_uniform(scene_seed, k, 2) * 4294967296))
        raw = [1.0 + rules.unit_area_spread * (2.0 * rng.random() - 1.0) for _ in range(n_units)]
        s = sum(raw)
        areas = tuple(gross * w / s for w in raw)
        buildings.append(BuildingSpec(sid, tenure, areas, draw))
    return SceneEntities(tuple(buildings), tuple(excluded), tuple(b.id for b in buildings))


def synthetic_table(n: int, scene_seed: int = 0):
    """Small synthetic scene table for tests and standalone runs."""
    rng = Rng(scene_seed)
    rows = []
    for i in range(n):
        rows.append({
            "id": f"b{i}",
            "area": rng.lognormal(4.7, 0.4),
            "storeys": rng.choice([1, 2, 2, 3, 3, 4, 5, 6]),
            "residential": True,
        })
    return rows
