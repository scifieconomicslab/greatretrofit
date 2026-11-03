"""Retrofit cooperative agents for v2 model."""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from .params import Params
from .banks import Bank
from .common.rng import make_rng


@dataclass
class Coop:
    """A retrofit cooperative.

    Attributes:
        id: Unique identifier.
        account: Current account balance (€).
        projects: List of building IDs currently in progress.
        completed_projects: List of completed building IDs.
        total_revenue: Cumulative revenue from completed projects.
        loans: Active loans from banks.
        loan_payments: Weekly loan payment obligations.
    """
    id: int
    account: float
    projects: List[int] = field(default_factory=list)
    completed_projects: List[int] = field(default_factory=list)
    total_revenue: float = 0.0
    loans: List[dict] = field(default_factory=list)
    loan_payments: float = 0.0

    def can_afford_project(self, project_cost: float, week_cost: float,
                           params: Params, building_map: Dict[int, 'Building']) -> bool:
        """Check if co-op can afford a new project given current commitments."""
        current_committed = sum(
            building_map[p_id].retrofit_cost for p_id in self.projects
        )
        # Calculate actual weekly outflow for current projects (scaled by size)
        weekly_outflow = sum(
            building_map[p_id].retrofit_cost / building_map[p_id].retrofit_time
            for p_id in self.projects if building_map[p_id].retrofit_time > 0
        ) + self.loan_payments
        # Project annual cash flow
        annual_outflow = weekly_outflow * 52
        # Payment-to-income cap: payments shouldn't exceed 30% of revenue
        if self.total_revenue > 0:
            pti = annual_outflow / self.total_revenue
            if pti > 0.3:
                return False
        return self.account >= current_committed + project_cost

    def get_project_buildings(self, building_map: Dict[int, 'Building']) -> List['Building']:
        """Get Building objects for current projects."""
        return [building_map[p_id] for p_id in self.projects if p_id in building_map]

    def weekly_cost(self, building_map: Dict[int, 'Building']) -> float:
        """Total weekly cost for all active projects (actual cost per project)."""
        return sum(
            building_map[p_id].retrofit_cost / building_map[p_id].retrofit_time
            for p_id in self.projects if building_map[p_id].retrofit_time > 0
        )

    def request_loan(self, project_cost: float, banks: List[Bank],
                     building_map: Dict[int, 'Building'], rng: np.random.Generator) -> Optional[dict]:
        """Request loan from best bank offer.

        Args:
            project_cost: Cost of the project.
            banks: List of available banks.
            building_map: Map of building ID to Building.
            rng: Random number generator.

        Returns:
            Loan terms dict or None if no loan available.
        """
        if not banks:
            return None

        # Get offers from all banks
        offers = []
        for bank in banks:
            if bank.can_lend(project_cost):
                terms = bank.offer_terms(project_cost, self.account)
                offers.append((bank.id, terms))

        if not offers:
            return None

        # Choose best offer (lowest rate)
        best_bank_id, best_terms = min(offers, key=lambda x: x[1]['rate'])
        best_bank = banks[best_bank_id]
        best_bank.make_loan(self.id, self.projects[-1] if self.projects else -1, best_terms)

        # Add to co-op's loans
        self.loans.append({
            'bank_id': best_bank_id,
            'building_id': self.projects[-1] if self.projects else -1,
            'principal': best_terms['amount'],
            'rate': best_terms['rate'],
            'remaining': best_terms['amount'],
        })
        self.loan_payments += best_terms['amount'] * best_terms['rate'] / 52
        self.account += best_terms['amount']  # Receive loan proceeds

        return best_terms

    def make_loan_payments(self, banks: List[Bank]) -> None:
        """Make weekly loan payments to banks."""
        for loan in self.loans[:]:  # Copy to allow modification
            if loan['remaining'] <= 0:
                continue
            bank = banks[loan['bank_id']]
            weekly_payment = loan['remaining'] * loan['rate'] / 52
            principal_paid = bank.receive_payment(self.id, weekly_payment)
            loan['remaining'] -= principal_paid
            self.account -= weekly_payment

            if loan['remaining'] <= 0:
                self.loan_payments -= weekly_payment
                self.loans.remove(loan)


def create_coops(params: Params) -> List[Coop]:
    """Create all co-ops with initial endowment.

    Args:
        params: Simulation parameters.

    Returns:
        List of Coop objects.
    """
    return [Coop(id=i, account=params.E) for i in range(params.n_co_ops)]