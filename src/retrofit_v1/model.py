"""Core simulation logic for v1 retrofit model."""
import copy
import numpy as np
from typing import List

from .params import Params
from .results import Result
from common.rng import make_rng


def run_simulation(params: Params) -> Result:
    """Run the v1 retrofit co-op simulation.

    Args:
        params: Simulation parameters.

    Returns:
        Result object containing weekly time series and summary statistics.
    """
    rng = make_rng(params.seed)

    n = params.n
    n_co_ops = params.n_co_ops
    E = params.E
    tau = params.tau
    surplus = params.surplus
    mean_time = params.mean_time
    time_var = params.time_var
    week_cost = params.week_cost
    run_time = params.run_time

    # Initialize building attributes (fixed for the run)
    to_do: List[int] = list(range(n))
    queued: List[int] = []
    times = rng.choice(2 * time_var, n) - time_var + mean_time
    costs = week_cost * times

    # Initialize co-op state
    projects: List[List[int]] = [[] for _ in range(n_co_ops)]
    finished: List[int] = []
    accounts = [E] * n_co_ops

    # Recording arrays (pre-allocate max size, trim at end)
    max_weeks = run_time + 1
    weekly_to_do = np.zeros(max_weeks, dtype=int)
    weekly_queued = np.zeros(max_weeks, dtype=int)
    weekly_in_progress = np.zeros(max_weeks, dtype=int)
    weekly_finished = np.zeros(max_weeks, dtype=int)
    weekly_total_accounts = np.zeros(max_weeks, dtype=float)
    weekly_with_capacity = np.zeros(max_weeks, dtype=int)

    t = 0
    while t < run_time:
        # Record state at start of week
        weekly_to_do[t] = len(to_do)
        weekly_queued[t] = len(queued)
        weekly_in_progress[t] = sum(len(p) for p in projects)
        weekly_finished[t] = len(finished)
        weekly_total_accounts[t] = sum(accounts)

        # 1. Buildings decide to request retrofits
        if to_do:
            n_requests = min(rng.poisson(tau), len(to_do))
            if n_requests > 0:
                selected = rng.choice(to_do, size=n_requests, replace=False)
                queued.extend(selected)
                to_do = list(set(to_do).difference(selected))

        # 2. Assign queued buildings to co-ops with capacity
        with_capacity_count = 0
        for b in queued.copy():
            estimate = costs[b]
            with_capacity = [
                c for c in range(n_co_ops)
                if sum(times[x] * week_cost for x in projects[c]) + estimate <= accounts[c]
            ]
            if not with_capacity:
                break
            with_capacity_count = len(with_capacity)
            c = rng.choice(with_capacity)
            projects[c].append(queued.pop(0))

        weekly_with_capacity[t] = with_capacity_count

        # 3. Co-ops do work on projects
        for c in range(n_co_ops):
            for p in copy.deepcopy(projects)[c]:
                if times[p] == 0:
                    # Project complete
                    projects[c].remove(p)
                    finished.append(p)
                    accounts[c] += (1 + surplus) * costs[p]
                else:
                    # Work in progress
                    if accounts[c] >= week_cost:
                        times[p] -= 1
                        accounts[c] -= week_cost

        t += 1

        if len(finished) == n:
            break

    # Record final week
    weekly_to_do[t] = len(to_do)
    weekly_queued[t] = len(queued)
    weekly_in_progress[t] = sum(len(p) for p in projects)
    weekly_finished[t] = len(finished)
    weekly_total_accounts[t] = sum(accounts)
    weekly_with_capacity[t] = 0

    # Trim arrays to actual length
    actual_weeks = t + 1
    return Result(
        weekly_to_do=weekly_to_do[:actual_weeks],
        weekly_queued=weekly_queued[:actual_weeks],
        weekly_in_progress=weekly_in_progress[:actual_weeks],
        weekly_finished=weekly_finished[:actual_weeks],
        weekly_total_accounts=weekly_total_accounts[:actual_weeks],
        weekly_with_capacity=weekly_with_capacity[:actual_weeks],
        finished=len(finished),
        total_weeks=actual_weeks,
        final_total_accounts=sum(accounts),
        params=params,
    )