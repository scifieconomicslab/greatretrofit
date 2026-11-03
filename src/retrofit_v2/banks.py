"""Bank agents for v2 retrofit model."""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional

from .params import Params
from common.rng import make_rng


@dataclass
class Bank:
    """A bank lending to retrofit co-ops.

    Attributes:
        id: Unique identifier.
        ltv_cap: Loan-to-value cap (fraction of project cost).
        rate_spread: Spread over base rate.
        capital: Bank's capital/reserves.
        loans: List of active loans.
        losses: Cumulative losses from defaults.
    """
    id: int
    ltv_cap: float
    rate_spread: float
    capital: float = 1_000_000.0
    loans: List[dict] = field(default_factory=list)
    losses: float = 0.0

    def can_lend(self, project_cost: float) -> bool:
        """Check if bank can lend for a project of given cost."""
        max_loan = self.ltv_cap * project_cost
        return self.capital >= max_loan

    def offer_terms(self, project_cost: float, coop_wealth: float) -> dict:
        """Generate loan terms for a project.

        Args:
            project_cost: Total project cost.
            coop_wealth: Co-op's current wealth (for risk assessment).

        Returns:
            Dict with loan terms.
        """
        max_loan = self.ltv_cap * project_cost
        # Risk premium: higher for higher LTV, lower for wealthier co-ops
        ltv = max_loan / project_cost
        risk_premium = 0.01 * (ltv / self.ltv_cap)  # Up to 1% extra
        # Wealth cushion reduces risk
        wealth_cushion = min(1.0, coop_wealth / project_cost) if project_cost > 0 else 0
        risk_premium *= (1 - 0.5 * wealth_cushion)

        rate = 0.03 + self.rate_spread + risk_premium  # Base 3% + spread + risk
        return {
            'amount': max_loan,
            'rate': rate,
            'ltv': ltv,
        }

    def make_loan(self, coop_id: int, building_id: int, terms: dict) -> None:
        """Record a new loan."""
        self.loans.append({
            'coop_id': coop_id,
            'building_id': building_id,
            'principal': terms['amount'],
            'rate': terms['rate'],
            'remaining': terms['amount'],
        })
        self.capital -= terms['amount']

    def receive_payment(self, coop_id: int, amount: float) -> float:
        """Process loan payment from co-op. Returns amount applied to principal."""
        for loan in self.loans:
            if loan['coop_id'] == coop_id and loan['remaining'] > 0:
                interest = loan['remaining'] * loan['rate'] / 52  # Weekly interest
                principal_paid = min(amount - interest, loan['remaining'])
                if principal_paid > 0:
                    loan['remaining'] -= principal_paid
                    self.capital += amount
                    return principal_paid
        return 0.0

    def check_defaults(self, coops: dict) -> List[int]:
        """Check for defaulted loans. Returns list of defaulted loan indices."""
        defaulted = []
        for i, loan in enumerate(self.loans):
            coop = coops[loan['coop_id']]
            # Simple default trigger: co-op account negative or severely underwater
            if coop.account < -loan['remaining'] * 0.1:
                defaulted.append(i)
        return defaulted

    def process_default(self, loan_idx: int) -> float:
        """Process a defaulted loan. Returns recovery amount."""
        loan = self.loans[loan_idx]
        # Recovery: assume 50% of collateral value
        recovery = loan['principal'] * 0.5
        self.losses += loan['remaining'] - recovery
        self.capital += recovery
        loan['remaining'] = 0
        return recovery

    def adjust_terms(self, recent_price_growth: float, recent_losses: float) -> None:
        """Adjust LTV cap and spread based on market conditions.

        Args:
            recent_price_growth: Recent price growth rate.
            recent_losses: Recent loss rate.
        """
        # Tighten after losses, loosen after price growth
        self.ltv_cap *= (1 - 0.1 * recent_losses + 0.05 * recent_price_growth)
        self.ltv_cap = np.clip(self.ltv_cap, 0.5, 0.95)

        self.rate_spread *= (1 + 0.2 * recent_losses - 0.1 * recent_price_growth)
        self.rate_spread = np.clip(self.rate_spread, 0.005, 0.05)


def create_banks(params: Params, rng: np.random.Generator) -> List[Bank]:
    """Create banks with heterogeneous LTV caps and spreads.

    Args:
        params: Simulation parameters.
        rng: Random number generator.

    Returns:
        List of Bank objects.
    """
    if params.n_banks == 0:
        return []

    banks = []
    for i in range(params.n_banks):
        # LTV cap: normal around mean
        ltv = rng.normal(params.bank_ltv_mean, params.bank_ltv_sd)
        ltv = np.clip(ltv, 0.5, 0.95)

        # Spread: normal around mean
        spread = rng.normal(params.bank_spread_mean, params.bank_spread_sd)
        spread = max(spread, 0.005)

        bank = Bank(id=i, ltv_cap=ltv, rate_spread=spread)
        banks.append(bank)

    return banks