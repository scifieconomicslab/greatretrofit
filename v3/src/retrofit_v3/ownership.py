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
    def consider_probability(self, base: float, neighbour_boost: float, adopted_share: float) -> float:
        """Monthly probability that a not-yet-adopted unit considers retrofitting."""


class OwnerOccupied(OwnershipStrategy):
    name = "owner_occupied"

    def can_adopt(self, building):
        return True

    def consider_probability(self, base, neighbour_boost, adopted_share):
        return min(1.0, base)


class Condo(OwnershipStrategy):
    """Each owner decides for their unit; neighbours' retrofits raise the odds.

    Shared-part voting and cost splitting are NOT implemented yet (pending
    economist answers, questions 13-14).
    """
    name = "condo"

    def can_adopt(self, building):
        return True

    def consider_probability(self, base, neighbour_boost, adopted_share):
        return min(1.0, base + neighbour_boost * adopted_share)


class Rental(OwnershipStrategy):
    """Stub: landlord logic arrives in model v2; no adoption for now."""
    name = "rental"

    def can_adopt(self, building):
        return False

    def consider_probability(self, base, neighbour_boost, adopted_share):
        return 0.0


OWNERSHIP = {s.name: s() for s in (OwnerOccupied, Condo, Rental)}
