"""Result dataclass for the v3 retrofit model."""
from dataclasses import dataclass, field
from typing import List, Tuple

from .frames import Frame
from .params import Params


@dataclass(frozen=True)
class AdoptionEvent:
    """One retrofit. All euro amounts are at adoption time (rebate is entitlement)."""
    month: int
    unit: int
    building: str
    quintile: int
    mode: str
    price: float
    from_savings: float
    loan: float
    savings_at_adoption: float
    credit_limit: float
    state_pays_now: float
    rebate: float
    rebate_lag_months: int
    tax_payable: float          # tax capacity left at the time (what the rebate was capped by)
    kind: str = "whole"         # whole (whole retrofit) | unit (unit part) | shared (this unit's share of a shared measure)
    base_cost: float = 0.0      # labour + materials; price - base_cost is vendor margin or public overhead
    subsidised: bool = False    # the delivery scheme applied (False: market purchase with no subsidy)


@dataclass(frozen=True)
class VoteEvent:
    """A shared measure passed. yes_share is the floor-area share of supporters at that moment."""
    month: int
    building: str
    yes_share: float
    threshold: float
    slots_used: int = 0         # public-service slots the shared work used (0 in the other modes)


@dataclass
class Result:
    params: Params
    frames: List[Frame] = field(default_factory=list)   # empty if params.keep_frames is False
    events: Tuple[AdoptionEvent, ...] = ()
    votes: Tuple[VoteEvent, ...] = ()
    final_frame: Frame = None
    n_units: int = 0
    n_buildings: int = 0

    @property
    def adopted_units(self) -> int:
        return self.final_frame["series"]["adopted_units"]

    @property
    def adoption_by_quintile(self):
        return self.final_frame["series"]["adoption_by_quintile"]
