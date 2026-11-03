"""Parameter dataclass for v2 retrofit model."""
from dataclasses import dataclass
from typing import Optional

from .common.validation import (
    validate_positive,
    validate_nonnegative,
    validate_probability,
    validate_integer_positive,
)


@dataclass(frozen=True)
class Params:
    """Parameters for the v2 retrofit co-op simulation.

    Base parameters (from v1):
        n: Total number of buildings needing retrofit.
        n_co_ops: Number of retrofit cooperatives.
        E: Initial endowment per co-op (euros).
        tau: Mean weekly request rate (Poisson).
        surplus: Co-op surplus rate (fraction, e.g., 0.2 for 20%).
        mean_time: Mean retrofit duration in weeks.
        time_var: Variance in retrofit duration (uniform range ±time_var).
        week_cost: Weekly cost per active project (euros).
        run_time: Maximum simulation time in weeks.
        seed: Random seed for reproducibility.

    New v2 parameters:
        n_households: Number of households (building owners).
        income_mean: Mean household income (€/year).
        income_cv: Coefficient of variation for income (lognormal).
        wealth_pareto_alpha: Pareto shape parameter for initial wealth.
        aspiration_mean: Mean aspiration level (0-100).
        aspiration_sd: Standard deviation of aspiration.
        search_length: Number of co-ops a household considers (default: all).
        n_neighbourhoods: Number of neighbourhoods for spatial structure.
    """
    # Base parameters
    n: int
    n_co_ops: int
    E: float
    tau: float
    surplus: float
    mean_time: float
    time_var: float
    week_cost: float
    run_time: int
    seed: Optional[int] = None

    # Household parameters
    n_households: int = 1000
    income_mean: float = 50000.0
    income_cv: float = 0.4
    wealth_pareto_alpha: float = 1.5
    aspiration_mean: float = 50.0
    aspiration_sd: float = 15.0

    # Search/matching parameters
    search_length: int = 0  # 0 = all co-ops

    # Spatial parameters
    n_neighbourhoods: int = 1

    # Bargaining parameters
    enable_bargaining: bool = False
    max_bid_shade: float = 0.2  # Max fraction below asking price buyers can bid
    seller_reservation_pct: float = 0.8  # Min fraction of asking price sellers accept

    # Bank parameters
    n_banks: int = 0
    bank_ltv_mean: float = 0.8
    bank_ltv_sd: float = 0.05
    bank_spread_mean: float = 0.02
    bank_spread_sd: float = 0.005

    # Default parameters
    enable_default: bool = False

    # Local demand parameters
    enable_local_demand: bool = False

    # Income process parameters
    income_ar1_rho: float = 0.0  # 0 = no AR(1) process
    income_shock_sd: float = 0.0
    unemployment_prob: float = 0.0

    # Investor market parameters
    enable_investors: bool = False
    investor_hurdle_mean: float = 0.05
    investor_hurdle_sd: float = 0.01

    # Stock evolution parameters
    enable_construction: bool = False
    build_cost: float = 150000.0
    construction_lag_weeks: int = 52
    depreciation_rate: float = 0.01  # Annual

    # Demographics parameters
    enable_demographics: bool = False
    birth_rate: float = 0.01
    death_rate: float = 0.01

    # Expectations parameters
    enable_heterogeneous_expectations: bool = False
    extrapolator_share: float = 0.5

    # Transaction costs
    transaction_cost_pct: float = 0.05
    moving_cost: float = 10000.0

    def __post_init__(self) -> None:
        # Base validation
        validate_integer_positive(self.n, "n")
        validate_integer_positive(self.n_co_ops, "n_co_ops")
        validate_positive(self.E, "E")
        validate_positive(self.tau, "tau")
        validate_probability(self.surplus, "surplus")
        validate_positive(self.mean_time, "mean_time")
        validate_nonnegative(self.time_var, "time_var")
        validate_positive(self.week_cost, "week_cost")
        validate_integer_positive(self.run_time, "run_time")
        if self.seed is not None:
            validate_integer_positive(self.seed, "seed")

        # Household validation
        validate_integer_positive(self.n_households, "n_households")
        validate_positive(self.income_mean, "income_mean")
        validate_nonnegative(self.income_cv, "income_cv")
        validate_positive(self.wealth_pareto_alpha, "wealth_pareto_alpha")
        validate_nonnegative(self.aspiration_mean, "aspiration_mean")
        validate_nonnegative(self.aspiration_sd, "aspiration_sd")

        # Search validation
        validate_nonnegative(self.search_length, "search_length")

        # Spatial validation
        validate_integer_positive(self.n_neighbourhoods, "n_neighbourhoods")

        # Bargaining validation
        if self.enable_bargaining:
            validate_probability(self.max_bid_shade, "max_bid_shade")
            validate_probability(self.seller_reservation_pct, "seller_reservation_pct")

        # Bank validation
        validate_nonnegative(self.n_banks, "n_banks")
        if self.n_banks > 0:
            validate_integer_positive(self.n_banks, "n_banks")
            validate_probability(self.bank_ltv_mean, "bank_ltv_mean")
            validate_nonnegative(self.bank_ltv_sd, "bank_ltv_sd")
            validate_nonnegative(self.bank_spread_mean, "bank_spread_mean")
            validate_nonnegative(self.bank_spread_sd, "bank_spread_sd")

        # Income process validation
        if self.income_ar1_rho > 0:
            validate_probability(self.income_ar1_rho, "income_ar1_rho")
            validate_nonnegative(self.income_shock_sd, "income_shock_sd")
            validate_probability(self.unemployment_prob, "unemployment_prob")

        # Investor validation
        if self.enable_investors:
            validate_positive(self.investor_hurdle_mean, "investor_hurdle_mean")
            validate_nonnegative(self.investor_hurdle_sd, "investor_hurdle_sd")

        # Construction validation
        if self.enable_construction:
            validate_positive(self.build_cost, "build_cost")
            validate_integer_positive(self.construction_lag_weeks, "construction_lag_weeks")
            validate_nonnegative(self.depreciation_rate, "depreciation_rate")

        # Demographics validation
        if self.enable_demographics:
            validate_probability(self.birth_rate, "birth_rate")
            validate_probability(self.death_rate, "death_rate")

        # Expectations validation
        if self.enable_heterogeneous_expectations:
            validate_probability(self.extrapolator_share, "extrapolator_share")

        # Transaction costs validation
        validate_probability(self.transaction_cost_pct, "transaction_cost_pct")
        validate_nonnegative(self.moving_cost, "moving_cost")