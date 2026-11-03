"""Retrofit cooperative agents for v2 model."""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional

from .params import Params
from common.rng import make_rng


@dataclass
class Coop:
    """A retrofit cooperative.

    Attributes:
        id: Unique identifier.
        account: Current account balance (€).
        projects: List of building IDs currently in progress.
        completed_projects: List of completed building IDs.
        total_revenue: Cumulative revenue from completed projects.
    """
    id: int
    account: float
    projects: List[int] = field(default_factory=list)
    completed_projects: List[int] = field(default_factory=list)
    total_revenue: float = 0.0

    def can_afford_project(self, project_cost: float, week_cost: float, params: Params) -> bool:
        """Check if co-op can afford a new project given current commitments.

        In v2, this considers the full estimated cost of all current projects
        plus the new one, similar to v1.
        """
        current_committed = sum(
            b.retrofit_cost for b in self.get_project_buildings()
        )
        return self.account >= current_committed + project_cost

    def get_project_buildings(self) -> List['Building']:
        """Get Building objects for current projects. Override in model."""
        return []

    def weekly_cost(self, week_cost: float) -> float:
        """Total weekly cost for all active projects."""
        return len(self.projects) * week_cost


def create_coops(params: Params) -> List[Coop]:
    """Create all co-ops with initial endowment.

    Args:
        params: Simulation parameters.

    Returns:
        List of Coop objects.
    """
    return [Coop(id=i, account=params.E) for i in range(params.n_co_ops)]