"""Result dataclass for v2 retrofit model."""
from dataclasses import dataclass
from typing import Optional
import numpy as np


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

        # New v2 monitors
        gini_wealth: Gini coefficient of household wealth at end.
        gini_wealth_trajectory: Gini coefficient per week.
        price_dispersion: Overall price dispersion (coefficient of variation).
        price_dispersion_within: Price dispersion within neighbourhoods.
        price_dispersion_between: Price dispersion between neighbourhoods.
        cash_buyer_share: Fraction of retrofits paid without borrowing.
        time_on_market_spread: Spread (max-min) of time-on-market across neighbourhoods.
        neighbourhood_time_on_market: Time on market per neighbourhood per week.
    """
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

    # v2 monitors
    gini_wealth: float = 0.0
    gini_wealth_trajectory: Optional[np.ndarray] = None
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

    def __len__(self) -> int:
        """Return number of recorded weeks."""
        return len(self.weekly_finished)