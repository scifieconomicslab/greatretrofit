"""Parameters for the v3 retrofit model.

EVERY default below marked ``# PLACEHOLDER`` is a stand-in awaiting the
economists' answers (open questions held outside this repository). Do not read
results from these numbers as findings. List: v3/docs/placeholders.md
(a test keeps that list in sync with this file).
"""
import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .common.validation import (
    validate_integer_positive,
    validate_nonnegative,
    validate_positive,
    validate_probability,
)
from .credit import CREDIT_ACCESS
from .entities import BuildingSpec
from .scene_entities import SceneRules

DELIVERY_MODES = ("rebate_market", "passthrough", "public_service")
ENERGY_SCENARIOS = ("flat", "rising", "shock")


@dataclass(frozen=True)
class Params:
    # --- run control (not economics) ---
    seed: int = 0
    scene_seed: int = 0
    horizon_months: int = 180            # 15 years, monthly step
    keep_frames: bool = True             # store frames in Result (False: only on_step sees them)
    buildings: Tuple[BuildingSpec, ...] = ()  # empty: synthetic scene of n_buildings
    n_buildings: int = 200               # used only when buildings is empty
    scene_rules: SceneRules = field(default_factory=SceneRules)

    # --- policy levers (the sliders) ---
    deduction_rate: float = 0.3          # PLACEHOLDER share of cost deductible from tax
    refundable: bool = False             # PLACEHOLDER refundable-credit toggle
    rebate_lag_months: int = 12          # PLACEHOLDER months until the rebate arrives; 0 = paid in the month of the retrofit; a fractional value is rounded half-to-even to whole months
    credit_access: str = "income_tested"  # PLACEHOLDER income_tested | open | none
    loan_rate: float = 0.04              # PLACEHOLDER annual loan rate
    delivery_mode: str = "rebate_market"  # PLACEHOLDER rebate_market | passthrough | public_service
    vendor_margin: float = 0.15          # PLACEHOLDER market vendor margin over base cost
    public_overhead: float = 0.10        # PLACEHOLDER public service overhead over base cost
    public_capacity: float = 0.05        # PLACEHOLDER max share of all units the service completes per year
    means_test: bool = False             # PLACEHOLDER restrict passthrough/public_service by income quintile
    means_test_max_quintile: int = 2     # PLACEHOLDER highest quintile eligible when means_test
    energy_scenario: str = "rising"      # PLACEHOLDER flat | rising | shock
    peer_effect: bool = True             # PLACEHOLDER condo: a neighbour's retrofit raises the chance of following
    loan_rate_risk_premium: float = 0.02  # PLACEHOLDER extra annual loan rate for households below the credit income threshold

    # --- tenure rule (placeholder; overrides the scene rules' shares for scene-built buildings via their stored draw; None keeps the tenure the scene rules gave) ---
    rental_share_single: Optional[float] = 0.10  # PLACEHOLDER share of single-unit buildings treated as rental (not modelled, never adopt)
    rental_share_multi: Optional[float] = 0.30   # PLACEHOLDER share of multi-unit buildings treated as rental

    # --- condo shared parts (vote) ---
    shared_measure: bool = True          # PLACEHOLDER condo buildings (2+ units) have shared parts that need a vote
    shared_share: float = 0.4            # PLACEHOLDER share of retrofit cost and of energy saving that sits in shared parts
    vote_threshold: float = 2.0 / 3.0    # PLACEHOLDER share of floor area that must vote yes (secondary source: two-thirds, unverified)

    # --- canvassing and the weekly time budget ---
    canvass_target_hours: float = 2.0    # PLACEHOLDER weekly hours an advocate would spend canvassing, if free time allows
    canvass_boost: float = 0.2           # PLACEHOLDER extra monthly consideration chance at full canvassing pressure (condo)
    canvass_saturation_hours: float = 6.0  # PLACEHOLDER weekly canvassing hours in a building that give full pressure
    waking_hours_per_week: float = 112.0  # PLACEHOLDER
    committed_hours_per_week: float = 50.0  # PLACEHOLDER chores, commuting, care: hours that are neither work nor free
    work_hours_by_quintile: Tuple[float, ...] = (42.0, 38.0, 36.0, 40.0, 48.0)  # PLACEHOLDER weekly working hours, quintile 1..5
    free_time_spread: float = 0.3        # PLACEHOLDER +/- relative spread of free hours across households

    # --- energy price paths ---
    energy_growth_flat: float = 0.0      # PLACEHOLDER annual real growth of savings value
    energy_growth_rising: float = 0.03   # PLACEHOLDER
    energy_growth_shock: float = 0.08    # PLACEHOLDER

    # --- retrofit physics and cost ---
    cost_per_m2: float = 300.0           # PLACEHOLDER base cost (labour+materials) per m2
    saving_per_m2_year: float = 20.0     # PLACEHOLDER annual energy bill saving per m2 at today's prices

    # --- household decision ---
    discount_rate: float = 0.04          # PLACEHOLDER annual discount rate
    consider_prob_base: float = 0.05     # PLACEHOLDER monthly chance a household considers retrofitting
    neighbour_boost: float = 0.30        # PLACEHOLDER extra consideration chance, times share of building adopted (condo)
    savings_usable_share: float = 1.0    # PLACEHOLDER share of savings available for the retrofit

    # --- credit ---
    credit_income_threshold: float = 25000.0  # PLACEHOLDER income needed under income_tested
    credit_loan_to_income: float = 1.0        # PLACEHOLDER loan cap as multiple of annual income
    loan_term_months: int = 120               # PLACEHOLDER

    # --- synthetic household population ---
    income_log_mean: float = 10.3        # PLACEHOLDER ln(annual income), ~ 30k
    income_log_sd: float = 0.5           # PLACEHOLDER
    tax_rate: float = 0.25               # PLACEHOLDER flat rate above allowance
    tax_free_allowance: float = 10000.0  # PLACEHOLDER
    savings_months_of_income: float = 3.0  # PLACEHOLDER mean liquid savings in months of income
    savings_scale: float = 1.0           # PLACEHOLDER multiplier on savings (0 = zero-savings world)
    savings_log_sd: float = 0.8          # PLACEHOLDER
    years_in_dwelling_min: float = 5.0   # PLACEHOLDER
    years_in_dwelling_max: float = 25.0  # PLACEHOLDER

    def __post_init__(self):
        validate_integer_positive(self.horizon_months, "horizon_months")
        validate_integer_positive(self.n_buildings, "n_buildings")
        validate_integer_positive(self.loan_term_months, "loan_term_months")
        validate_nonnegative(self.rebate_lag_months, "rebate_lag_months")
        if not math.isfinite(self.rebate_lag_months):
            raise ValueError(f"rebate_lag_months must be finite, got {self.rebate_lag_months}")
        object.__setattr__(self, "rebate_lag_months", int(round(self.rebate_lag_months)))   # whole months, half-to-even (as JS pyRound)
        for name in ("deduction_rate", "vendor_margin", "public_overhead", "public_capacity",
                     "consider_prob_base", "neighbour_boost", "savings_usable_share", "tax_rate",
                     "shared_share", "canvass_boost", "free_time_spread"):
            validate_probability(getattr(self, name), name)
        for name in ("cost_per_m2", "saving_per_m2_year", "income_log_sd", "savings_log_sd",
                     "years_in_dwelling_min", "years_in_dwelling_max",
                     "canvass_saturation_hours", "waking_hours_per_week"):
            validate_positive(getattr(self, name), name)
        for name in ("loan_rate", "loan_rate_risk_premium", "canvass_target_hours", "committed_hours_per_week",
                     "discount_rate", "credit_income_threshold", "credit_loan_to_income",
                     "tax_free_allowance", "savings_months_of_income", "savings_scale"):
            validate_nonnegative(getattr(self, name), name)
        for name in ("rental_share_single", "rental_share_multi"):
            if getattr(self, name) is not None:
                validate_probability(getattr(self, name), name)
        if not 0.0 < self.vote_threshold <= 1.0:
            raise ValueError("vote_threshold must be in (0, 1]")
        object.__setattr__(self, "work_hours_by_quintile", tuple(float(x) for x in self.work_hours_by_quintile))
        if len(self.work_hours_by_quintile) != 5 or any(x < 0 for x in self.work_hours_by_quintile):
            raise ValueError("work_hours_by_quintile must be 5 non-negative numbers")
        if self.years_in_dwelling_max < self.years_in_dwelling_min:
            raise ValueError("years_in_dwelling_max must be >= years_in_dwelling_min")
        if self.delivery_mode not in DELIVERY_MODES:
            raise ValueError(f"delivery_mode must be one of {DELIVERY_MODES}, got {self.delivery_mode!r}")
        if self.credit_access not in CREDIT_ACCESS:
            raise ValueError(f"credit_access must be one of {CREDIT_ACCESS}, got {self.credit_access!r}")
        if self.energy_scenario not in ENERGY_SCENARIOS:
            raise ValueError(f"energy_scenario must be one of {ENERGY_SCENARIOS}, got {self.energy_scenario!r}")
        if not 1 <= self.means_test_max_quintile <= 5:
            raise ValueError("means_test_max_quintile must be in 1..5")

    @property
    def energy_growth_annual(self) -> float:
        return getattr(self, f"energy_growth_{self.energy_scenario}")
