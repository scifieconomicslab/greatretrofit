"""Parameter dataclass for v2 retrofit model."""
from dataclasses import dataclass
from typing import Optional

from common.validation import (
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