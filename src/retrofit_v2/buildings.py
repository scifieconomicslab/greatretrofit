"""Building agents for v2 retrofit model."""
import numpy as np
from dataclasses import dataclass
from typing import Optional

from .params import Params
from common.rng import make_rng


@dataclass
class Building:
    """A building needing retrofit.

    Attributes:
        id: Unique identifier.
        size: Size factor (1.0 = baseline).
        age: Age in years.
        location_quality: Location amenity score (0-1).
        neighbourhood: Neighbourhood index.
        retrofit_time: Weeks needed for retrofit.
        retrofit_cost: Total cost for retrofit.
        owner_id: ID of household that owns this building.
        state: Current state ('to_do', 'queued', 'in_progress', 'finished').
        assigned_coop: ID of assigned co-op (if any).
        weeks_remaining: Weeks left in retrofit.
    """
    id: int
    size: float
    age: float
    location_quality: float
    neighbourhood: int
    retrofit_time: int
    retrofit_cost: float
    owner_id: int
    state: str = 'to_do'
    assigned_coop: Optional[int] = None
    weeks_remaining: int = 0


def create_buildings(params: Params, households, rng: np.random.Generator):
    """Create buildings with heterogeneous attributes.

    Args:
        params: Simulation parameters.
        households: List of Household objects.
        rng: Random number generator.

    Returns:
        List of Building objects.
    """
    n = params.n

    # Building attributes
    # Size: lognormal around 1.0
    sizes = rng.lognormal(0, 0.3, n)

    # Age: uniform 0-80 years
    ages = rng.uniform(0, 80, n)

    # Location quality: beta distribution (most average, some very good/bad)
    location_quality = rng.beta(2, 2, n)

    # Neighbourhood assignment (match household if possible)
    if params.n_neighbourhoods > 1:
        neighbourhoods = np.array([h.neighbourhood for h in households[:n]])
    else:
        neighbourhoods = np.zeros(n, dtype=int)

    # Retrofit time: base time scaled by size and age
    # Base time ~ mean_time ± time_var
    base_times = rng.uniform(
        params.mean_time - params.time_var,
        params.mean_time + params.time_var,
        n
    )
    # Scale by size and age factor
    age_factor = 1.0 + ages / 100.0  # Older buildings take longer
    retrofit_times = np.round(base_times * sizes * age_factor).astype(int)
    retrofit_times = np.maximum(retrofit_times, 1)  # At least 1 week

    # Retrofit cost: weekly_cost * time * size factor
    retrofit_costs = params.week_cost * retrofit_times * sizes

    buildings = []
    for i in range(n):
        b = Building(
            id=i,
            size=sizes[i],
            age=ages[i],
            location_quality=location_quality[i],
            neighbourhood=neighbourhoods[i],
            retrofit_time=retrofit_times[i],
            retrofit_cost=retrofit_costs[i],
            owner_id=households[i].id if i < len(households) else i,
        )
        buildings.append(b)
        # Link building to household
        if i < len(households):
            households[i].building_id = i

    return buildings