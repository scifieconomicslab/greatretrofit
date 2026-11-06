"""Model entity specs (inputs to the simulation)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

TENURES = ("owner_occupied", "condo", "rental")


@dataclass(frozen=True)
class BuildingSpec:
    id: str
    tenure: str
    unit_areas: Tuple[float, ...]   # floor area (m2) per dwelling unit

    @property
    def units(self) -> int:
        return len(self.unit_areas)

    @property
    def floor_area(self) -> float:
        return sum(self.unit_areas)
