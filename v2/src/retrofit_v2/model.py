"""Core simulation logic for v2 retrofit model."""
import copy
import numpy as np
from typing import List, Dict, Optional

from .params import Params
from .results import Result
from .households import Household, create_households
from .buildings import Building, create_buildings, create_new_building, depreciate_buildings
from .coops import Coop, create_coops
from .banks import Bank, create_banks
from .common.rng import make_rng


def gini_coefficient(values: np.ndarray) -> float:
    """Calculate Gini coefficient of an array of values.
    
    Handles negative values by shifting to non-negative.
    """
    if len(values) == 0:
        return 0.0
    values = np.array(values)
    # Shift to non-negative if needed
    min_val = np.min(values)
    if min_val < 0:
        values = values - min_val
    values = np.sort(values)
    n = len(values)
    cumsum = np.cumsum(values)
    if cumsum[-1] == 0:
        return 0.0
    return (2 * np.sum((np.arange(1, n+1) * values))) / (n * cumsum[-1]) - (n + 1) / n


def run_simulation(params: Params) -> Result:
    """Run the v2 retrofit co-op simulation.

    Args:
        params: Simulation parameters.

    Returns:
        Result object containing weekly time series and summary statistics.
    """
    rng = make_rng(params.seed)

    # Create agents - households as dict keyed by ID for stable references
    household_list = create_households(params, rng)
    households: Dict[int, Household] = {h.id: h for h in household_list}
    buildings = create_buildings(params, household_list, rng)
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

    # Additional weekly time series
    weekly_failed_negotiations = np.zeros(max_weeks, dtype=int)
    weekly_defaults = np.zeros(max_weeks, dtype=int)
    weekly_cumulative_defaults = np.zeros(max_weeks, dtype=int)
    weekly_investor_purchases = np.zeros(max_weeks, dtype=int)
    weekly_new_construction = np.zeros(max_weeks, dtype=int)
    weekly_avg_queue_wait = np.zeros(max_weeks, dtype=float)
    weekly_max_queue_wait = np.zeros(max_weeks, dtype=int)
    weekly_bank_losses = np.zeros(max_weeks, dtype=float)
    weekly_cumulative_bank_losses = np.zeros(max_weeks, dtype=float)
    weekly_loan_volume = np.zeros(max_weeks, dtype=float)
    weekly_loan_payments = np.zeros(max_weeks, dtype=float)
    weekly_coop_revenue = np.zeros(max_weeks, dtype=float)
    weekly_unemployment_rate = np.zeros(max_weeks, dtype=float)
    weekly_avg_retrofit_time = np.zeros(max_weeks, dtype=float)
    weekly_avg_retrofit_cost = np.zeros(max_weeks, dtype=float)

    # Per-neighbourhood weekly
    if params.n_neighbourhoods > 1:
        weekly_finished_per_nh = np.zeros((params.n_neighbourhoods, max_weeks), dtype=int)
        weekly_queue_per_nh = np.zeros((params.n_neighbourhoods, max_weeks), dtype=int)
        weekly_avg_price_per_nh = np.zeros((params.n_neighbourhoods, max_weeks), dtype=float)
    else:
        weekly_finished_per_nh = None
        weekly_queue_per_nh = None
        weekly_avg_price_per_nh = None

    # v2 monitors
    weekly_gini = np.zeros(max_weeks, dtype=float)
    weekly_income_gini = np.zeros(max_weeks, dtype=float)
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
    investor_purchases = 0
    new_construction_count = 0
    total_finished_count = 0  # Total buildings that have ever completed retrofit

    # Income trajectories (sample subset for memory)
    income_sample_size = min(100, params.n_households)
    household_income_trajectories = np.zeros((income_sample_size, max_weeks), dtype=float)

    # Population trajectory
    population_trajectory = np.zeros(max_weeks, dtype=int)

    # Next building ID for new construction
    next_building_id = params.n
    next_household_id = params.n_households

    t = 0
    while t < params.run_time:
        # Record state at start of week
        weekly_to_do[t] = len(to_do)
        weekly_queued[t] = len(queued)
        weekly_in_progress[t] = sum(len(c.projects) for c in coops)
        weekly_finished[t] = len(finished)
        weekly_total_accounts[t] = sum(c.account for c in coops)

        # Calculate Gini of household wealth
        wealths = np.array([h.wealth for h in households.values()])
        weekly_gini[t] = gini_coefficient(wealths)

        # Calculate Gini of household income (sample)
        n_households = len(households)
        if n_households > 0:
            sample_size = min(income_sample_size, n_households)
            household_ids = list(households.keys())
            sample_idx = rng.choice(len(household_ids), sample_size, replace=False)
            sample_household_ids = [household_ids[i] for i in sample_idx]
            incomes_sample = np.array([households[h_id].income for h_id in sample_household_ids])
            weekly_income_gini[t] = gini_coefficient(incomes_sample)

            # Record income trajectories
            for idx, h_id in enumerate(sample_household_ids):
                household_income_trajectories[idx, t] = households[h_id].income

            # Unemployment rate
            unemployed = sum(1 for h in households.values() if h.unemployed)
            weekly_unemployment_rate[t] = unemployed / n_households

        # Population
        population_trajectory[t] = len(households)

        # Queue wait times
        if len(queued) > 0:
            wait_times = [t - building_entry_week[b_id] for b_id in queued]
            weekly_avg_queue_wait[t] = np.mean(wait_times)
            weekly_max_queue_wait[t] = max(wait_times)

        # Co-op metrics
        weekly_coop_revenue[t] = sum(c.total_revenue for c in coops)

        # Per-neighbourhood queue
        if params.n_neighbourhoods > 1:
            for nh in range(params.n_neighbourhoods):
                nh_queue = [b_id for b_id in queued if building_map[b_id].neighbourhood == nh]
                weekly_queue_per_nh[nh, t] = len(nh_queue)

        # Bank metrics
        weekly_bank_losses[t] = sum(b.losses for b in banks)
        weekly_cumulative_bank_losses[t] = sum(b.losses for b in banks)

        # 1. Households decide to request retrofits
        if to_do:
            requesting = []
            for b_id in to_do:
                building = building_map[b_id]
                owner = households.get(building.owner_id)
                if owner and owner.wants_retrofit(rng):
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
            owner = households.get(building.owner_id)
            if owner and params.enable_bargaining:
                bid = owner.bid_price(building.retrofit_cost, params, rng)
                reservation = building.retrofit_cost * params.seller_reservation_pct
                if bid < reservation:
                    # Negotiation failed - building returns to queued
                    coop.projects.remove(building.id)
                    building.state = 'queued'
                    building.assigned_coop = None
                    queued.append(building.id)
                    weekly_failed_negotiations[t] += 1
                    continue

                building.negotiated_price = bid
            else:
                building.negotiated_price = building.retrofit_cost

            # Co-op may request loan for the project
            total_purchases += 1
            if params.n_banks > 0 and rng.random() < 0.5:
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
            if params.n_banks > 0:
                coop.make_loan_payments(banks)

            for p_id in copy.deepcopy(coop.projects):
                building = building_map[p_id]
                # Calculate actual weekly cost for this building
                weekly_cost = building.retrofit_cost / building.retrofit_time if building.retrofit_time > 0 else 0
                if building.weeks_remaining <= 0:
                    # Project complete
                    coop.projects.remove(p_id)
                    coop.completed_projects.append(p_id)
                    building.state = 'finished'
                    building.assigned_coop = None
                    finished.append(p_id)
                    total_finished_count += 1

                    # Record average retrofit time/cost for this week
                    weekly_avg_retrofit_time[t] = building.retrofit_time
                    weekly_avg_retrofit_cost[t] = building.retrofit_cost

                    # Per-neighbourhood finished
                    if params.n_neighbourhoods > 1:
                        nh = building.neighbourhood
                        weekly_finished_per_nh[nh, t] += 1
                        # Track prices for average
                        if weekly_avg_price_per_nh[nh, t] == 0:
                            weekly_avg_price_per_nh[nh, t] = building.retrofit_cost
                        else:
                            weekly_avg_price_per_nh[nh, t] = (weekly_avg_price_per_nh[nh, t] + building.retrofit_cost) / 2

                    # Co-op receives payment with surplus
                    price = getattr(building, 'negotiated_price', building.retrofit_cost)
                    revenue = (1 + params.surplus) * price
                    coop.account += revenue
                    coop.total_revenue += revenue

                    # Household pays (wealth decreases by negotiated price)
                    owner = households.get(building.owner_id)
                    if owner:
                        owner.wealth = max(0, owner.wealth - price)
                else:
                    # Work in progress
                    if coop.account >= weekly_cost:
                        building.weeks_remaining -= 1
                        coop.account -= weekly_cost

        # 4. Bank default processing
        if params.enable_default and params.n_banks > 0:
            for bank in banks:
                defaulted = bank.check_defaults({c.id: c for c in coops})
                for loan_idx in defaulted:
                    bank.process_default(loan_idx)
                    default_count += 1

        # Record weekly financial metrics
        weekly_defaults[t] = default_count
        weekly_cumulative_defaults[t] = default_count
        weekly_bank_losses[t] = sum(b.losses for b in banks)
        weekly_cumulative_bank_losses[t] = sum(b.losses for b in banks)
        weekly_loan_volume[t] = total_loan_volume
        weekly_loan_payments[t] = sum(c.loan_payments for c in coops)

        # 5. Income process update
        if params.income_ar1_rho > 0:
            for h in households.values():
                h.update_income(params, rng)

        # 6. Investor market activity
        if params.enable_investors:
            # Track which buildings have been purchased this week to avoid double-sales
            purchased_this_week = set()
            for h in list(households.values()):
                if h.is_investor:
                    # Check finished buildings for investment opportunities
                    for b_id in finished:
                        if b_id in purchased_this_week:
                            continue  # Already purchased this week
                        building = building_map[b_id]
                        if building.owner_id == h.id:
                            continue  # Already own
                        if h.wants_investment(building, params, rng):
                            # Investor purchases building
                            investor_purchases += 1
                            purchased_this_week.add(b_id)
                            # Transfer ownership
                            old_owner = households.get(building.owner_id)
                            if old_owner:
                                old_owner.building_id = None
                            building.owner_id = h.id
                            h.building_id = b_id
                            # Pay price
                            h.wealth -= building.retrofit_cost
                            # Remove from finished list - no longer available for re-purchase
                            if b_id in finished:
                                finished.remove(b_id)

            # Record weekly investor purchases
            weekly_investor_purchases[t] = investor_purchases

        # 7. Demographics: births, deaths, household formation
        if params.enable_demographics:
            # Deaths
            dead_household_ids = []
            for h_id, h in list(households.items()):
                death_prob = params.death_rate / 52.0  # Weekly probability
                if h.age > 65:
                    death_prob *= 3  # Higher for elderly
                if rng.random() < death_prob:
                    dead_household_ids.append(h_id)
                    # Household dies - building becomes available
                    if h.building_id is not None:
                        building = building_map[h.building_id]
                        building.owner_id = -1
                        building.state = 'to_do'
                        if building.id not in to_do:
                            to_do.append(building.id)

            for h_id in dead_household_ids:
                del households[h_id]

            # Births / new household formation
            births = rng.poisson(len(households) * params.birth_rate / 52.0)
            for _ in range(births):
                # New household with random attributes
                new_id = next_household_id
                next_household_id += 1
                sigma = np.sqrt(np.log(1 + params.income_cv**2))
                mu = np.log(params.income_mean) - sigma**2 / 2
                income = rng.lognormal(mu, sigma)
                wealth = params.income_mean / 10.0 * (1 - rng.random())**(-1.0 / params.wealth_pareto_alpha)
                aspiration = np.clip(rng.normal(params.aspiration_mean, params.aspiration_sd), 0, 100)
                affordability = np.clip(rng.normal(0.33, 0.1), 0.05, 0.6)
                taste_weights = rng.dirichlet([2.0, 2.0, 2.0])
                taste_shock = rng.normal(0, 0.5)
                neighbourhood = rng.integers(0, params.n_neighbourhoods)
                age = 25
                is_investor = rng.random() < 0.15
                hurdle_rate = np.clip(rng.normal(params.investor_hurdle_mean, params.investor_hurdle_sd), 0.02, 0.15)
                expectations_type = 'extrapolator' if rng.random() < params.extrapolator_share else 'fundamentalist'

                new_h = Household(
                    id=new_id,
                    income=income,
                    wealth=wealth,
                    aspiration=aspiration,
                    affordability=affordability,
                    taste_weights=taste_weights,
                    taste_shock=taste_shock,
                    neighbourhood=neighbourhood,
                    age=age,
                    is_investor=is_investor,
                    hurdle_rate=hurdle_rate,
                    expectations_type=expectations_type,
                )
                new_h.income_history.append(income)
                households[new_id] = new_h

        # 8. Building depreciation
        if params.depreciation_rate > 0:
            depreciate_buildings(list(building_map.values()), params, dt=1/52.0)

        # 9. New construction
        if params.enable_construction:
            # Check if price > build cost in any neighbourhood
            if params.n_neighbourhoods > 1:
                for nh in range(params.n_neighbourhoods):
                    nh_finished = [b_id for b_id in finished
                                  if building_map[b_id].neighbourhood == nh]
                    if len(nh_finished) > 10:
                        prices = [building_map[b_id].retrofit_cost for b_id in nh_finished]
                        avg_price = np.mean(prices)
                        if avg_price > params.build_cost * 1.2:  # 20% premium triggers construction
                            if rng.random() < 0.1:  # 10% chance per week
                                new_b = create_new_building(params, nh, rng, next_building_id)
                                next_building_id += 1
                                buildings.append(new_b)
                                building_map[new_b.id] = new_b
                                to_do.append(new_b.id)
                                new_construction_count += 1
            else:
                if len(finished) > 10:
                    prices = [building_map[b_id].retrofit_cost for b_id in finished]
                    avg_price = np.mean(prices)
                    if avg_price > params.build_cost * 1.2:
                        if rng.random() < 0.1:
                            new_b = create_new_building(params, 0, rng, next_building_id)
                            next_building_id += 1
                            buildings.append(new_b)
                            building_map[new_b.id] = new_b
                            to_do.append(new_b.id)
                            new_construction_count += 1

        # Record weekly new construction
        weekly_new_construction[t] = new_construction_count

        t += 1

        if len(finished) == params.n and not params.enable_construction:
            break

    # Record final week
    weekly_to_do[t] = len(to_do)
    weekly_queued[t] = len(queued)
    weekly_in_progress[t] = sum(len(c.projects) for c in coops)
    weekly_finished[t] = len(finished)
    weekly_total_accounts[t] = sum(c.account for c in coops)
    weekly_with_capacity[t] = 0
    wealths = np.array([h.wealth for h in households.values()])
    weekly_gini[t] = gini_coefficient(wealths)
    population_trajectory[t] = len(households)

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
        finished=total_finished_count,
        total_weeks=actual_weeks,
        final_total_accounts=sum(c.account for c in coops),
        params=params,
        gini_wealth=gini_wealth,
        gini_wealth_trajectory=weekly_gini[:actual_weeks],
        weekly_income_gini=weekly_income_gini[:actual_weeks],
        price_dispersion=price_dispersion,
        price_dispersion_within=price_dispersion_within,
        price_dispersion_between=price_dispersion_between,
        cash_buyer_share=cash_buyer_share,
        time_on_market_spread=time_on_market_spread,
        neighbourhood_time_on_market=neighbourhood_time_on_market[:, :actual_weeks] if neighbourhood_time_on_market is not None else None,
        bank_losses=bank_losses,
        default_count=default_count,
        total_loan_volume=total_loan_volume,
        household_income_trajectories=household_income_trajectories[:, :actual_weeks],
        investor_purchases=investor_purchases,
        new_construction_count=new_construction_count,
        population_trajectory=population_trajectory[:actual_weeks],
        # Additional weekly time series
        weekly_failed_negotiations=weekly_failed_negotiations[:actual_weeks],
        weekly_defaults=weekly_defaults[:actual_weeks],
        weekly_cumulative_defaults=weekly_cumulative_defaults[:actual_weeks],
        weekly_investor_purchases=weekly_investor_purchases[:actual_weeks],
        weekly_new_construction=weekly_new_construction[:actual_weeks],
        weekly_avg_queue_wait=weekly_avg_queue_wait[:actual_weeks],
        weekly_max_queue_wait=weekly_max_queue_wait[:actual_weeks],
        weekly_bank_losses=weekly_bank_losses[:actual_weeks],
        weekly_cumulative_bank_losses=weekly_cumulative_bank_losses[:actual_weeks],
        weekly_loan_volume=weekly_loan_volume[:actual_weeks],
        weekly_loan_payments=weekly_loan_payments[:actual_weeks],
        weekly_coop_revenue=weekly_coop_revenue[:actual_weeks],
        weekly_unemployment_rate=weekly_unemployment_rate[:actual_weeks],
        weekly_avg_retrofit_time=weekly_avg_retrofit_time[:actual_weeks],
        weekly_avg_retrofit_cost=weekly_avg_retrofit_cost[:actual_weeks],
        # Per-neighbourhood weekly
        weekly_finished_per_nh=weekly_finished_per_nh[:, :actual_weeks] if weekly_finished_per_nh is not None else None,
        weekly_queue_per_nh=weekly_queue_per_nh[:, :actual_weeks] if weekly_queue_per_nh is not None else None,
        weekly_avg_price_per_nh=weekly_avg_price_per_nh[:, :actual_weeks] if weekly_avg_price_per_nh is not None else None,
    )