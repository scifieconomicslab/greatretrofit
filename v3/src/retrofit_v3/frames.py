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
    shared_state: str     # none (no shared parts) | pending (vote not passed) | approved
    vote_yes_share: float  # floor-area share of supporters, 0 when shared_state is none
    units_cannot_front: int  # not-yet-retrofitted units that cannot finance what they still have to pay now (0 for rental)


class SeriesPoint(TypedDict):
    adoption_by_quintile: List[float]       # 5 values, share of units retrofitted
    rebate_per_euro: List[Optional[float]]  # 5; public transfer entitled per euro of price, adopters so far; null if none
    can_front_cost: List[Optional[float]]   # 5; share of not-yet-retrofitted units able to finance the price now; null if none left
    cost_per_retrofit: Optional[float]      # mean price paid per retrofit so far; null if none
    public_cost: float                      # cumulative public outlay (vendor payments + rebates paid)
    bills_saved: float                      # cumulative household energy bills saved
    state_counts: dict                      # building state -> count
    adopted_units: int
    cost_per_retrofit_parts: Optional[dict]  # {base, markup}: mean base cost and mean vendor margin / public overhead; sum = cost_per_retrofit
    canvass_hours_by_quintile: List[float]  # 5; mean weekly canvassing hours per household
    leisure_hours_by_quintile: List[float]  # 5; mean weekly free hours left after canvassing (never negative)
    net_cash_by_quintile: List[Optional[float]]  # 5; mean cumulative household net cash of households that paid for works; null if none
    shared_counts: dict                     # {pending, approved}: buildings with shared parts by vote state
    tenure_counts: dict                     # {owner_occupied, condo, rental}: buildings by tenure (the placeholder tenure rule's outcome)


class Frame(TypedDict):
    schema: int
    t: int            # months elapsed
    year: float
    buildings: List[BuildingFrame]
    series: SeriesPoint
