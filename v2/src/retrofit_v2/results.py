"""Result dataclass for v2 retrofit model."""
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


def _empty_array():
    return np.array([])


def _empty_2d_array():
    return np.zeros((0, 0))


@dataclass
class Result:
    """Results from a v2 retrofit simulation run.

    Attributes:
        weekly_to_do: Buildings not yet requesting retrofit per week.
        weekly_queued: Buildings waiting for co-op assignment per week.
        weekly_in_progress: Buildings currently being retrofitted per week.
        weekly_finished: Cumulative completed buildings per week.
        weekly_total_accounts: Total capital across all co-ops per week.
        weekly_with_capacity: Number of co-ops with capacity per week.
        finished: Total buildings completed at end of simulation.
        total_weeks: Number of weeks simulated.
        final_total_accounts: Total capital across all co-ops at end.
        params: Parameters used for this run.

        # Additional weekly time series
        weekly_failed_negotiations: Failed bargaining attempts per week.
        weekly_defaults: Defaults occurring per week.
        weekly_cumulative_defaults: Cumulative defaults per week.
        weekly_investor_purchases: Investor acquisitions per week.
        weekly_new_construction: New buildings started per week.
        weekly_avg_queue_wait: Average weeks in queue per week.
        weekly_max_queue_wait: Maximum weeks in queue per week.
        weekly_bank_losses: Bank losses incurred per week.
        weekly_cumulative_bank_losses: Cumulative bank losses per week.
        weekly_loan_volume: Cumulative loan volume originated per week.
        weekly_loan_payments: Total loan payments made per week.
        weekly_coop_revenue: Cumulative co-op revenue per week.
        weekly_unemployment_rate: Fraction of households unemployed per week.
        weekly_avg_retrofit_time: Average retrofit duration of completions per week.
        weekly_avg_retrofit_cost: Average retrofit cost of completions per week.

        # Per-neighbourhood weekly
        weekly_finished_per_nh: Finished buildings per neighbourhood per week.
        weekly_queue_per_nh: Queued buildings per neighbourhood per week.
        weekly_avg_price_per_nh: Average retrofit price per neighbourhood per week.

        # v2 monitors
        gini_wealth: Gini coefficient of household wealth at end.
        gini_wealth_trajectory: Gini coefficient per week.
        price_dispersion: Overall price dispersion (coefficient of variation).
        price_dispersion_within: Price dispersion within neighbourhoods.
        price_dispersion_between: Price dispersion between neighbourhoods.
        cash_buyer_share: Fraction of retrofits paid without borrowing.
        time_on_market_spread: Spread (max-min) of time-on-market across neighbourhoods.
        neighbourhood_time_on_market: Time on market per neighbourhood per week.

        # Bank/financial monitors
        bank_losses: Total bank losses.
        default_count: Number of defaults.
        total_loan_volume: Total originated.

        # Market realism monitors
        household_income_trajectories: Sample income paths.
        investor_purchases: Investor acquisitions.
        new_construction_count: New buildings added.
        population_trajectory: Household count over time.

        # Additional monitors
        weekly_cumulative_defaults: Cumulative defaults per week.
        weekly_investor_purchases: Investor purchases per week.
        weekly_new_construction: New construction per week.
        weekly_avg_queue_wait: Average queue wait time.
        weekly_max_queue_wait: Maximum queue wait time.
        weekly_bank_losses: Bank losses per week.
        weekly_cumulative_bank_losses: Cumulative bank losses per week.
        weekly_loan_volume: Loan volume per week.
        weekly_loan_payments: Loan payments per week.
        weekly_coop_revenue: Co-op revenue per week.
        weekly_unemployment_rate: Unemployment rate per week.
        weekly_avg_retrofit_time: Average retrofit time per week.
        weekly_avg_retrofit_cost: Average retrofit cost per week.
        weekly_finished_per_nh: Finished per neighbourhood per week.
        weekly_queue_per_nh: Queue per neighbourhood per week.
        weekly_avg_price_per_nh: Average price per neighbourhood per week.
    """
    # Base weekly time series (from v1)
    weekly_to_do: np.ndarray
    weekly_queued: np.ndarray
    weekly_in_progress: np.ndarray
    weekly_finished: np.ndarray
    weekly_total_accounts: np.ndarray
    weekly_with_capacity: np.ndarray
    finished: int
    total_weeks: int
    final_total_accounts: float
    params: Optional["Params"] = None  # type: ignore[name-defined]

    # Additional weekly time series
    weekly_failed_negotiations: np.ndarray = field(default_factory=_empty_array)
    weekly_defaults: np.ndarray = field(default_factory=_empty_array)
    weekly_cumulative_defaults: np.ndarray = field(default_factory=_empty_array)
    weekly_investor_purchases: np.ndarray = field(default_factory=_empty_array)
    weekly_new_construction: np.ndarray = field(default_factory=_empty_array)
    weekly_avg_queue_wait: np.ndarray = field(default_factory=_empty_array)
    weekly_max_queue_wait: np.ndarray = field(default_factory=_empty_array)
    weekly_bank_losses: np.ndarray = field(default_factory=_empty_array)
    weekly_cumulative_bank_losses: np.ndarray = field(default_factory=_empty_array)
    weekly_loan_volume: np.ndarray = field(default_factory=_empty_array)
    weekly_loan_payments: np.ndarray = field(default_factory=_empty_array)
    weekly_coop_revenue: np.ndarray = field(default_factory=_empty_array)
    weekly_unemployment_rate: np.ndarray = field(default_factory=_empty_array)
    weekly_avg_retrofit_time: np.ndarray = field(default_factory=_empty_array)
    weekly_avg_retrofit_cost: np.ndarray = field(default_factory=_empty_array)

    # Per-neighbourhood weekly
    weekly_finished_per_nh: Optional[np.ndarray] = None
    weekly_queue_per_nh: Optional[np.ndarray] = None
    weekly_avg_price_per_nh: Optional[np.ndarray] = None

    # v2 monitors
    gini_wealth: float = 0.0
    gini_wealth_trajectory: Optional[np.ndarray] = None
    weekly_income_gini: Optional[np.ndarray] = None
    price_dispersion: float = 0.0
    price_dispersion_within: float = 0.0
    price_dispersion_between: float = 0.0
    cash_buyer_share: float = 0.0
    time_on_market_spread: float = 0.0
    neighbourhood_time_on_market: Optional[np.ndarray] = None

    # Bank/financial monitors
    bank_losses: float = 0.0
    default_count: int = 0
    total_loan_volume: float = 0.0

    # Market realism monitors
    household_income_trajectories: Optional[np.ndarray] = None
    investor_purchases: int = 0
    new_construction_count: int = 0
    population_trajectory: Optional[np.ndarray] = None

    def __len__(self) -> int:
        """Return number of recorded weeks."""
        return len(self.weekly_finished)