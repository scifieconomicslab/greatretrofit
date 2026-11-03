"""Household agents for v2 retrofit model."""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional

from .params import Params
from .common.rng import make_rng


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
        age: Age of household head.
        is_investor: Whether this household is an investor/landlord.
        hurdle_rate: Required return for investment (if investor).
        expectations_type: 'extrapolator' or 'fundamentalist'.
        unemployed: Whether currently unemployed.
        income_history: List of past income values.
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
    age: int = 30
    is_investor: bool = False
    hurdle_rate: float = 0.05
    expectations_type: str = 'fundamentalist'
    unemployed: bool = False
    income_history: List[float] = field(default_factory=list)

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

    def update_income(self, params: 'Params', rng: np.random.Generator) -> None:
        """Update income based on AR(1) process with unemployment shocks.

        Args:
            params: Simulation parameters.
            rng: Random number generator.
        """
        if params.income_ar1_rho == 0:
            return

        # Record current income
        self.income_history.append(self.income)

        # Unemployment shock
        if not self.unemployed and rng.random() < params.unemployment_prob:
            self.unemployed = True
            self.income *= 0.3  # Unemployment benefit ~30% of income
        elif self.unemployed and rng.random() < 0.1:  # 10% chance to find job per week
            self.unemployed = False
            # Income recovers with AR(1) process
            log_income = np.log(self.income)
            shock = rng.normal(0, params.income_shock_sd)
            log_income = params.income_ar1_rho * log_income + (1 - params.income_ar1_rho) * np.log(params.income_mean) + shock
            self.income = np.exp(log_income)
        elif not self.unemployed:
            # Normal AR(1) income process
            log_income = np.log(self.income)
            shock = rng.normal(0, params.income_shock_sd)
            log_income = params.income_ar1_rho * log_income + (1 - params.income_ar1_rho) * np.log(params.income_mean) + shock
            self.income = np.exp(log_income)

    def wants_investment(self, building: 'Building', params: 'Params', rng: np.random.Generator) -> bool:
        """Decide whether to purchase building as investment.

        Args:
            building: Building to evaluate.
            params: Simulation parameters.
            rng: Random number generator.

        Returns:
            True if household wants to invest.
        """
        if not params.enable_investors or not self.is_investor:
            return False

        # Expected rental yield
        # Simplified: rent = 5% of building value per year
        rent = building.retrofit_cost * 0.05
        yield_rate = rent / building.retrofit_cost

        # Adjust expectations
        if self.expectations_type == 'extrapolator':
            # Extrapolate recent price growth (simplified)
            expected_growth = 0.02  # 2% annual
        else:
            expected_growth = 0.0

        expected_return = yield_rate + expected_growth
        return expected_return > self.hurdle_rate

    def age_one_week(self) -> None:
        """Age the household by one week."""
        self.age += 1 / 52.0


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
    sigma = np.sqrt(np.log(1 + params.income_cv**2))
    mu = np.log(params.income_mean) - sigma**2 / 2
    incomes = rng.lognormal(mu, sigma, n)

    # Wealth: Pareto distribution (independent of income)
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

    # Ages: uniform 25-75
    ages = rng.integers(25, 75, n)

    # Investor status
    is_investor = rng.random(n) < 0.15  # 15% are investors

    # Hurdle rates for investors
    hurdle_rates = rng.normal(params.investor_hurdle_mean, params.investor_hurdle_sd, n)
    hurdle_rates = np.clip(hurdle_rates, 0.02, 0.15)

    # Expectations type
    expectations = np.where(
        rng.random(n) < params.extrapolator_share,
        'extrapolator',
        'fundamentalist'
    )

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
            age=ages[i],
            is_investor=is_investor[i],
            hurdle_rate=hurdle_rates[i],
            expectations_type=expectations[i],
        )
        h.income_history.append(incomes[i])
        households.append(h)

    return households