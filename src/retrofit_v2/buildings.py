"""Building agents for v2 retrofit model."""
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

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
        condition: Building condition (0-1, 1 = perfect).
        depreciated_value: Current depreciated value.
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
    condition: float = 1.0
    depreciated_value: float = 0.0


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

    # Initial condition: newer buildings better condition
    conditions = np.clip(1.0 - ages / 100.0 + rng.normal(0, 0.1, n), 0.2, 1.0)

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
            condition=conditions[i],
            depreciated_value=retrofit_costs[i] * conditions[i],
        )
        buildings.append(b)
        # Link building to household
        if i < len(households):
            households[i].building_id = i

    return buildings


def create_new_building(params: Params, neighbourhood: int, rng: np.random.Generator, next_id: int) -> Building:
    """Create a newly constructed building.

    Args:
        params: Simulation parameters.
        neighbourhood: Neighbourhood index.
        rng: Random number generator.
        next_id: Next available building ID.

    Returns:
        New Building object.
    """
    # New buildings: smaller, modern, good condition
    size = rng.lognormal(0, 0.2)
    age = 0.0
    location_quality = rng.beta(3, 2)  # Slightly better locations
    condition = 1.0

    base_time = rng.uniform(
        params.mean_time - params.time_var,
        params.mean_time + params.time_var,
    )
    retrofit_time = max(1, int(np.round(base_time * size)))
    retrofit_cost = params.week_cost * retrofit_time * size

    return Building(
        id=next_id,
        size=size,
        age=age,
        location_quality=location_quality,
        neighbourhood=neighbourhood,
        retrofit_time=retrofit_time,
        retrofit_cost=retrofit_cost,
        owner_id=-1,  # No owner yet
        condition=condition,
        depreciated_value=retrofit_cost,
    )


def depreciate_buildings(buildings: List[Building], params: Params, dt: float = 1/52) -> None:
    """Apply depreciation to all buildings.

    Args:
        buildings: List of buildings.
        params: Simulation parameters.
        dt: Time step in years (default: 1 week).
    """
    if params.depreciation_rate == 0:
        return

    for b in buildings:
        if b.state == 'finished':
            # Retrofitted buildings depreciate slower
            dep_rate = params.depreciation_rate * 0.5
        else:
            dep_rate = params.depreciation_rate

        b.age += dt
        b.condition = max(0.1, b.condition - dep_rate * dt)
        b.depreciated_value = b.retrofit_cost * b.condition