"""Core simulation logic for v2 retrofit model."""
import copy
import numpy as np
from typing import List, Dict, Optional

from .params import Params
from .results import Result
from .households import Household, create_households
from .buildings import Building, create_buildings
from .coops import Coop, create_coops
from .banks import Bank, create_banks
from common.rng import make_rng


def gini_coefficient(values: np.ndarray) -> float:
    """Calculate Gini coefficient of an array of values."""
    if len(values) == 0:
        return 0.0
    values = np.sort(values)
    n = len(values)
    cumsum = np.cumsum(values)
    return (2 * np.sum((np.arange(1, n+1) * values))) / (n * cumsum[-1]) - (n + 1) / n


def run_simulation(params: Params) -> Result:
    """Run the v2 retrofit co-op simulation.

    Args:
        params: Simulation parameters.

    Returns:
        Result object containing weekly time series and summary statistics.
    """
    rng = make_rng(params.seed)

    # Create agents
    households = create_households(params, rng)
    buildings = create_buildings(params, households, rng)
    coops = create_coops(params)
    banks = create_banks(params, rng)

    # Map building ID -> Building for quick lookup
    building_map = {b.id: b for b in buildings}

    # Initialize state lists
    to_do = [b.id for b in buildings if b.state == 'to_do']
    queued = []
    finished = []

    # Recording arrays
    max_weeks = params.run_time + 1
    weekly_to_do = np.zeros(max_weeks, dtype=int)
    weekly_queued = np.zeros(max_weeks, dtype=int)
    weekly_in_progress = np.zeros(max_weeks, dtype=int)
    weekly_finished = np.zeros(max_weeks, dtype=int)
    weekly_total_accounts = np.zeros(max_weeks, dtype=float)
    weekly_with_capacity = np.zeros(max_weeks, dtype=int)

    # v2 monitors
    weekly_gini = np.zeros(max_weeks, dtype=float)
    if params.n_neighbourhoods > 1:
        neighbourhood_time_on_market = np.zeros((params.n_neighbourhoods, max_weeks), dtype=float)
    else:
        neighbourhood_time_on_market = None

    # Time-on-market tracking per building
    building_entry_week = {b.id: -1 for b in buildings}

    # Financial tracking
    total_loan_volume = 0.0
    default_count = 0
    cash_purchases = 0
    total_purchases = 0

    t = 0
    while t < params.run_time:
        # Record state at start of week
        weekly_to_do[t] = len(to_do)
        weekly_queued[t] = len(queued)
        weekly_in_progress[t] = sum(len(c.projects) for c in coops)
        weekly_finished[t] = len(finished)
        weekly_total_accounts[t] = sum(c.account for c in coops)

        # Calculate Gini of household wealth
        wealths = np.array([h.wealth for h in households])
        weekly_gini[t] = gini_coefficient(wealths)

        # 1. Households decide to request retrofits
        if to_do:
            requesting = []
            for b_id in to_do:
                building = building_map[b_id]
                owner = households[building.owner_id]
                if owner.wants_retrofit(rng):
                    requesting.append(b_id)

            for b_id in requesting:
                building = building_map[b_id]
                building.state = 'queued'
                building_entry_week[b_id] = t
                queued.append(b_id)

            to_do = [b_id for b_id in to_do if b_id not in requesting]

        # 2. Assign queued buildings to co-ops (with bargaining)
        with_capacity_count = 0
        for b_id in queued.copy():
            building = building_map[b_id]
            estimate = building.retrofit_cost

            # Determine eligible co-ops
            if params.search_length > 0 and params.search_length < params.n_co_ops:
                # Limited search: household sees random sample of co-ops
                search_pool = rng.choice(params.n_co_ops, size=params.search_length, replace=False)
            else:
                search_pool = list(range(params.n_co_ops))

            with_capacity = []
            for c_id in search_pool:
                coop = coops[c_id]
                current_committed = sum(building_map[p_id].retrofit_cost for p_id in coop.projects)
                if coop.account >= current_committed + estimate:
                    with_capacity.append(c_id)

            if not with_capacity:
                break

            with_capacity_count = len(with_capacity)
            c_id = rng.choice(with_capacity)
            coop = coops[c_id]
            coop.projects.append(queued.pop(0))
            building = building_map[coop.projects[-1]]
            building.state = 'in_progress'
            building.assigned_coop = c_id
            building.weeks_remaining = building.retrofit_time

            # Bargaining: household bids below asking price
            owner = households[building.owner_id]
            if params.enable_bargaining:
                bid = owner.bid_price(building.retrofit_cost, params, rng)
                reservation = building.retrofit_cost * params.seller_reservation_pct
                if bid < reservation:
                    # Negotiation failed - building returns to queued
                    coop.projects.remove(building.id)
                    building.state = 'queued'
                    building.assigned_coop = None
                    queued.append(building.id)
                    continue

                # Successful negotiation at bid price
                building.negotiated_price = bid
            else:
                building.negotiated_price = building.retrofit_cost

            # Co-op may request loan for the project
            total_purchases += 1
            if params.n_banks > 0 and rng.random() < 0.5:  # 50% chance to seek financing
                loan_terms = coop.request_loan(building.negotiated_price, banks, building_map, rng)
                if loan_terms:
                    total_loan_volume += loan_terms['amount']
                    building.financed = True
                else:
                    building.financed = False
                    cash_purchases += 1
            else:
                building.financed = False
                cash_purchases += 1

        weekly_with_capacity[t] = with_capacity_count

        # 3. Co-ops do work on projects and make loan payments
        for coop in coops:
            # Make loan payments first
            if params.n_banks > 0:
                coop.make_loan_payments(banks)

            for p_id in copy.deepcopy(coop.projects):
                building = building_map[p_id]
                if building.weeks_remaining <= 0:
                    # Project complete
                    coop.projects.remove(p_id)
                    coop.completed_projects.append(p_id)
                    building.state = 'finished'
                    building.assigned_coop = None
                    finished.append(p_id)

                    # Co-op receives payment with surplus
                    price = getattr(building, 'negotiated_price', building.retrofit_cost)
                    revenue = (1 + params.surplus) * price
                    coop.account += revenue
                    coop.total_revenue += revenue

                    # Household pays (wealth decreases by negotiated price)
                    owner = households[building.owner_id]
                    owner.wealth = max(0, owner.wealth - price)
                else:
                    # Work in progress
                    if coop.account >= params.week_cost:
                        building.weeks_remaining -= 1
                        coop.account -= params.week_cost

        # 4. Bank default processing
        if params.enable_default and params.n_banks > 0:
            for bank in banks:
                defaulted = bank.check_defaults({c.id: c for c in coops})
                for loan_idx in defaulted:
                    bank.process_default(loan_idx)
                    default_count += 1

        t += 1

        if len(finished) == params.n:
            break

    # Record final week
    weekly_to_do[t] = len(to_do)
    weekly_queued[t] = len(queued)
    weekly_in_progress[t] = sum(len(c.projects) for c in coops)
    weekly_finished[t] = len(finished)
    weekly_total_accounts[t] = sum(c.account for c in coops)
    weekly_with_capacity[t] = 0
    wealths = np.array([h.wealth for h in households])
    weekly_gini[t] = gini_coefficient(wealths)

    actual_weeks = t + 1

    # Calculate final monitors
    gini_wealth = weekly_gini[actual_weeks - 1]

    # Price dispersion
    finished_costs = np.array([building_map[b_id].retrofit_cost for b_id in finished])
    price_dispersion = np.std(finished_costs) / np.mean(finished_costs) if len(finished_costs) > 0 else 0.0

    # Price dispersion within/between neighbourhoods
    if params.n_neighbourhoods > 1 and len(finished_costs) > 0:
        within_dispersions = []
        between_means = []
        for nh in range(params.n_neighbourhoods):
            nh_costs = [building_map[b_id].retrofit_cost for b_id in finished
                        if building_map[b_id].neighbourhood == nh]
            if len(nh_costs) > 1:
                within_dispersions.append(np.std(nh_costs) / np.mean(nh_costs))
            if len(nh_costs) > 0:
                between_means.append(np.mean(nh_costs))
        price_dispersion_within = np.mean(within_dispersions) if within_dispersions else 0.0
        price_dispersion_between = np.std(between_means) / np.mean(between_means) if len(between_means) > 1 else 0.0
    else:
        price_dispersion_within = 0.0
        price_dispersion_between = 0.0

    # Cash buyer share
    cash_buyer_share = cash_purchases / total_purchases if total_purchases > 0 else 1.0

    # Bank losses
    bank_losses = sum(b.losses for b in banks)

    # Time on market spread
    if neighbourhood_time_on_market is not None:
        nh_times = []
        for nh in range(params.n_neighbourhoods):
            nh_finished = [b_id for b_id in finished
                          if building_map[b_id].neighbourhood == nh]
            if nh_finished:
                times = [actual_weeks - building_entry_week[b_id] for b_id in nh_finished]
                nh_times.append(np.mean(times))
            else:
                nh_times.append(0)
        time_on_market_spread = max(nh_times) - min(nh_times) if nh_times else 0.0
    else:
        time_on_market_spread = 0.0

    # Trim arrays
    return Result(
        weekly_to_do=weekly_to_do[:actual_weeks],
        weekly_queued=weekly_queued[:actual_weeks],
        weekly_in_progress=weekly_in_progress[:actual_weeks],
        weekly_finished=weekly_finished[:actual_weeks],
        weekly_total_accounts=weekly_total_accounts[:actual_weeks],
        weekly_with_capacity=weekly_with_capacity[:actual_weeks],
        finished=len(finished),
        total_weeks=actual_weeks,
        final_total_accounts=sum(c.account for c in coops),
        params=params,
        gini_wealth=gini_wealth,
        gini_wealth_trajectory=weekly_gini[:actual_weeks],
        price_dispersion=price_dispersion,
        price_dispersion_within=price_dispersion_within,
        price_dispersion_between=price_dispersion_between,
        cash_buyer_share=cash_buyer_share,
        time_on_market_spread=time_on_market_spread,
        neighbourhood_time_on_market=neighbourhood_time_on_market[:, :actual_weeks] if neighbourhood_time_on_market is not None else None,
        bank_losses=bank_losses,
        default_count=default_count,
        total_loan_volume=total_loan_volume,
    )