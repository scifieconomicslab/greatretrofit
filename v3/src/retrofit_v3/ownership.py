"""Ownership-type strategies. Swap rules without touching the core loop."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import BuildingSpec


class OwnershipStrategy(ABC):
    name: str

    @abstractmethod
    def can_adopt(self, building: BuildingSpec) -> bool:
        """May units in this building retrofit at all?"""

    @abstractmethod
    def consider_probability(self, base: float, neighbour_boost: float, adopted_share: float,
                             canvass_boost: float = 0.0, canvass_pressure: float = 0.0) -> float:
        """Monthly probability that a not-yet-adopted unit considers retrofitting."""

    def has_shared_parts(self, building: BuildingSpec) -> bool:
        """Does a retrofit of this building include parts that need a building-level decision?"""
        return False


class OwnerOccupied(OwnershipStrategy):
    name = "owner_occupied"

    def can_adopt(self, building):
        return True

    def consider_probability(self, base, neighbour_boost, adopted_share, canvass_boost=0.0, canvass_pressure=0.0):
        return min(1.0, base)


class Condo(OwnershipStrategy):
    """Each owner decides for their unit; neighbours' retrofits raise the odds.

    Shared parts (windows, facade, roof) are decided by a vote in the model loop
    (model.py); this strategy only says which buildings have them.
    """
    name = "condo"

    def can_adopt(self, building):
        return True

    def consider_probability(self, base, neighbour_boost, adopted_share, canvass_boost=0.0, canvass_pressure=0.0):
        return min(1.0, base + neighbour_boost * adopted_share + canvass_boost * canvass_pressure)

    def has_shared_parts(self, building):
        return building.units >= 2


class Rental(OwnershipStrategy):
    """Stub: landlord logic arrives in model v2; no adoption for now."""
    name = "rental"

    def can_adopt(self, building):
        return False

    def consider_probability(self, base, neighbour_boost, adopted_share, canvass_boost=0.0, canvass_pressure=0.0):
        return 0.0


OWNERSHIP = {s.name: s() for s in (OwnerOccupied, Condo, Rental)}
