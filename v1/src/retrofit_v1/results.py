"""Result dataclass for v1 retrofit model."""
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class Result:
    """Results from a v1 retrofit simulation run.

    Attributes:
        weekly_to_do: Buildings not yet requesting retrofit per week.
        weekly_queued: Buildings waiting for co-op assignment per week.
        weekly_in_progress: Buildings currently being retrofitted per week.
        weekly_finished: Cumulative completed buildings per week.
        weekly_total_accounts: Total capital across all co-ops per week.
        weekly_with_capacity: Number of co-ops with capacity for current queued building per week.
        finished: Total buildings completed at end of simulation.
        total_weeks: Number of weeks simulated.
        final_total_accounts: Total capital across all co-ops at end.
        params: Parameters used for this run (optional, for traceability).
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

    def __len__(self) -> int:
        """Return number of recorded weeks."""
        return len(self.weekly_finished)