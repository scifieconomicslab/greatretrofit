"""Scene table -> model buildings and units (model-from-scene, plan D3).

Input rows: dicts with id, area (footprint m2), storeys, residential (bool).
All rules and numbers are PLACEHOLDERS (see v3/docs/placeholders.md). Randomness
uses hash_uniform keyed by a *scene seed* separate from the model seed.
Does not depend on paperdolls.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Tuple

from .common.rng import Rng, hash_uniform
from .entities import MAX_UNITS_PER_BUILDING, BuildingSpec
from .common.validation import validate_positive, validate_probability


# MAX_UNITS_PER_BUILDING (entities.py): a scene building above it (a huge footprint times many levels: bad geometry) keeps its floor area but is split
# into this many units, and build_entities reports it in `capped` (and warns). Same constant in runtime.js (SM-9).


def scene_key(row_id, index: int) -> str:
    """The id of a scene row. A row without an id is "#<index>" (index in the scene's building list), the paperdolls convention (viz/packruntime.js sceneKey). Same rule in runtime.js."""
    return f"#{index}" if row_id is None else str(row_id)


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
    capped: Tuple[Tuple[str, int], ...] = ()       # (scene id, dwellings before the cap): buildings split into MAX_UNITS_PER_BUILDING units


def build_entities(rows: Iterable[Mapping], rules: SceneRules = SceneRules(), scene_seed: int = 0) -> SceneEntities:
    buildings, excluded, capped = [], [], []
    for k, row in enumerate(rows):
        sid = scene_key(row.get("id"), k)
        if not row.get("residential", False):
            excluded.append((sid, "non_residential"))
            continue
        area, storeys = float(row["area"]), int(row.get("storeys") or 1)
        gross = area * storeys * rules.usable_fraction
        if not (area > 0 and storeys > 0 and math.isfinite(gross)):      # NaN, inf, zero, negative
            excluded.append((sid, "invalid_geometry"))
            continue
        n_units = max(1, round(gross / rules.avg_unit_area))
        if n_units > MAX_UNITS_PER_BUILDING:
            capped.append((sid, n_units))
            n_units = MAX_UNITS_PER_BUILDING
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
    if capped:
        warnings.warn(f"{len(capped)} scene building(s) have more than {MAX_UNITS_PER_BUILDING} dwellings by the scene rules (first: {capped[0][0]} with {capped[0][1]}); "
                      f"each is modelled with {MAX_UNITS_PER_BUILDING} units", stacklevel=2)
    return SceneEntities(tuple(buildings), tuple(excluded), tuple(b.id for b in buildings), tuple(capped))


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
