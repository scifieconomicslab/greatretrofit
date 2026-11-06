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
    tax_payable: float


@dataclass
class Result:
    params: Params
    frames: List[Frame] = field(default_factory=list)   # empty if params.keep_frames is False
    events: Tuple[AdoptionEvent, ...] = ()
    final_frame: Frame = None
    n_units: int = 0
    n_buildings: int = 0

    @property
    def adopted_units(self) -> int:
        return len(self.events)

    @property
    def adoption_by_quintile(self):
        return self.final_frame["series"]["adoption_by_quintile"]
