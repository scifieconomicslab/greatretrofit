"""Parameter dataclass for v1 retrofit model."""
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
    """Parameters for the v1 retrofit co-op simulation.

    Attributes:
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
    """
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

    def __post_init__(self) -> None:
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