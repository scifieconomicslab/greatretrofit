"""Model entity specs (inputs to the simulation)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

TENURES = ("owner_occupied", "condo", "rental")


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
