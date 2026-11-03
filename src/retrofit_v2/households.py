"""Household agents for v2 retrofit model."""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional

from .params import Params
from common.rng import make_rng


@dataclass
class Household:
    """A household (building owner) in the retrofit market.

    Attributes:
        id: Unique identifier.
        income: Annual income (€).
        wealth: Current wealth/savings (€).
        aspiration: Aspiration level (0-100), probability of requesting retrofit.
        affordability: Maximum fraction of income for retrofit payments.
        taste_weights: Weights for building attributes [size, age, location].
        taste_shock: Random taste shock for each building.
        neighbourhood: Neighbourhood index.
        building_id: ID of owned building (if any).
    """
    id: int
    income: float
    wealth: float
    aspiration: float
    affordability: float
    taste_weights: np.ndarray  # shape (3,)
    taste_shock: float
    neighbourhood: int
    building_id: Optional[int] = None

    def wants_retrofit(self, rng: np.random.Generator) -> bool:
        """Decide whether to request a retrofit this week."""
        return rng.random() < (self.aspiration / 100.0)

    def utility_for_building(self, building: 'Building') -> float:
        """Calculate utility for a specific building."""
        # Utility = weighted sum of attributes + taste shock
        attrs = np.array([building.size, -building.age, building.location_quality])
        return float(np.dot(self.taste_weights, attrs) + self.taste_shock)

    def max_affordable_cost(self) -> float:
        """Maximum total cost household can afford."""
        return self.affordability * self.income

    def can_afford(self, cost: float) -> bool:
        """Check if household can afford a retrofit of given cost."""
        return cost <= self.max_affordable_cost()

    def bid_price(self, asking_price: float, params: 'Params', rng: np.random.Generator) -> float:
        """Calculate bid price below asking price based on willingness to pay.

        Args:
            asking_price: The asking price (retrofit cost).
            params: Simulation parameters.
            rng: Random number generator.

        Returns:
            Bid price (may be lower than asking).
        """
        if not params.enable_bargaining:
            return asking_price

        # Bid shade: random up to max_bid_shade based on affordability pressure
        affordability_pressure = 1.0 - (self.wealth / max(1, self.max_affordable_cost()))
        affordability_pressure = np.clip(affordability_pressure, 0, 1)

        max_shade = params.max_bid_shade * affordability_pressure
        shade = rng.uniform(0, max_shade)

        bid = asking_price * (1 - shade)
        # Don't bid more than can afford
        return min(bid, self.max_affordable_cost())

    def reservation_price(self, asking_price: float, params: 'Params') -> float:
        """Minimum price household would accept as seller (not used for owners, but for symmetry)."""
        return asking_price * params.seller_reservation_pct


def create_households(params: Params, rng: np.random.Generator) -> List[Household]:
    """Create all households with heterogeneous attributes.

    Args:
        params: Simulation parameters.
        rng: Random number generator.

    Returns:
        List of Household objects.
    """
    n = params.n_households

    # Income: lognormal with given mean and CV
    # For lognormal: mean = exp(mu + sigma^2/2), CV = sqrt(exp(sigma^2) - 1)
    # Solve for mu, sigma
    sigma = np.sqrt(np.log(1 + params.income_cv**2))
    mu = np.log(params.income_mean) - sigma**2 / 2
    incomes = rng.lognormal(mu, sigma, n)

    # Wealth: Pareto distribution (independent of income)
    # Pareto: x_m * (1 - U)^(-1/alpha), where x_m is scale
    # Use income_mean/10 as scale for reasonable magnitude
    wealth_scale = params.income_mean / 10.0
    u = rng.random(n)
    wealths = wealth_scale * (1 - u)**(-1.0 / params.wealth_pareto_alpha)

    # Aspiration: truncated normal around aspiration_mean
    aspirations = rng.normal(params.aspiration_mean, params.aspiration_sd, n)
    aspirations = np.clip(aspirations, 0, 100)

    # Affordability: truncated normal around 0.33 (33% of income)
    affordability = rng.normal(0.33, 0.1, n)
    affordability = np.clip(affordability, 0.05, 0.6)

    # Taste weights: Dirichlet distribution for [size, -age, location]
    taste_weights = rng.dirichlet([2.0, 2.0, 2.0], n)

    # Taste shocks: normal
    taste_shocks = rng.normal(0, 0.5, n)

    # Neighbourhood assignment
    neighbourhoods = rng.integers(0, params.n_neighbourhoods, n)

    households = []
    for i in range(n):
        h = Household(
            id=i,
            income=incomes[i],
            wealth=wealths[i],
            aspiration=aspirations[i],
            affordability=affordability[i],
            taste_weights=taste_weights[i],
            taste_shock=taste_shocks[i],
            neighbourhood=neighbourhoods[i],
        )
        households.append(h)

    return households