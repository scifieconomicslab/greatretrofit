"""Frame contract emitted every step (see v3/docs/frame-schema.md).

Plain JSON-serialisable TypedDicts. Treat as a stable API consumed by the
paperdolls model pack: add fields freely, never rename/remove without bumping
FRAME_SCHEMA_VERSION.
"""
from typing import List, Optional, TypedDict

FRAME_SCHEMA_VERSION = 1
BUILDING_STATES = ("not_retrofitted", "partial", "retrofitted", "not_modelled")


class BuildingFrame(TypedDict):
    id: str              # scene id
    state: str           # one of BUILDING_STATES
    tenure: str          # owner_occupied | condo | rental
    units: int
    adopted_share: float  # retrofitted units / units, 0..1
    income_q_mean: float  # mean income quintile (1..5) of the building's households


class SeriesPoint(TypedDict):
    adoption_by_quintile: List[float]       # 5 values, share of units retrofitted
    rebate_per_euro: List[Optional[float]]  # 5; public transfer entitled per euro of price, adopters so far; null if none
    can_front_cost: List[Optional[float]]   # 5; share of not-yet-retrofitted units able to finance the price now; null if none left
    cost_per_retrofit: Optional[float]      # mean price paid per retrofit so far; null if none
    public_cost: float                      # cumulative public outlay (vendor payments + rebates paid)
    bills_saved: float                      # cumulative household energy bills saved
    state_counts: dict                      # building state -> count
    adopted_units: int


class Frame(TypedDict):
    schema: int
    t: int            # months elapsed
    year: float
    buildings: List[BuildingFrame]
    series: SeriesPoint
