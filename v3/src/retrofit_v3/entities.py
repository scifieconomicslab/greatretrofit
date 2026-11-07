"""Model entity specs (inputs to the simulation)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

TENURES = ("owner_occupied", "condo", "rental")

# Largest number of dwellings of one building: scene rules cap a building at it (scene_entities.py, SM-9) and explicit buildings above it are rejected.
# Same constant in runtime.js.
MAX_UNITS_PER_BUILDING = 1000


@dataclass(frozen=True)
class BuildingSpec:
    id: str
    tenure: str
    unit_areas: Tuple[float, ...]   # floor area (m2) per dwelling unit
    rental_draw: Optional[float] = None  # the building's uniform draw in [0,1) behind the placeholder tenure rule (scene-built buildings only);
    #                                      lets Params.rental_share_* re-assign rental without re-binding the scene

    @property
    def units(self) -> int:
        return len(self.unit_areas)

    @property
    def floor_area(self) -> float:
        return sum(self.unit_areas)


def validate_building_spec(b, index: int) -> None:
    """Rules for an explicit building (SM-3), the same as the JS validateBuilding: a BuildingSpec with a string id, a known tenure, 1..MAX_UNITS_PER_BUILDING
    dwellings, every dwelling area a finite number above 0, and a rental draw that is None or in [0, 1]. Raises ValueError naming the building."""
    from .common.validation import validate_finite
    if not isinstance(b, BuildingSpec):
        raise ValueError(f"buildings[{index}] must be a BuildingSpec, got {b!r}")
    where = f"buildings[{index}] ({b.id!r})"
    if not isinstance(b.id, str):
        raise ValueError(f"buildings[{index}]: id must be a string, got {b.id!r}")
    if b.tenure not in TENURES:
        raise ValueError(f"{where}: tenure must be one of {TENURES}, got {b.tenure!r}")
    if not isinstance(b.unit_areas, (tuple, list)):
        raise ValueError(f"{where}: unit_areas must be a list of areas, got {b.unit_areas!r}")
    if not 1 <= len(b.unit_areas) <= MAX_UNITS_PER_BUILDING:
        raise ValueError(f"{where}: needs 1 to {MAX_UNITS_PER_BUILDING} dwellings, got {len(b.unit_areas)}")
    for k, a in enumerate(b.unit_areas):
        validate_finite(a, f"{where}: unit_areas[{k}]")
        if a <= 0:
            raise ValueError(f"{where}: unit_areas[{k}] must be positive, got {a}")
    if b.rental_draw is not None:
        validate_finite(b.rental_draw, f"{where}: rental_draw")
        if not 0 <= b.rental_draw <= 1:
            raise ValueError(f"{where}: rental_draw must be in [0, 1], got {b.rental_draw}")
