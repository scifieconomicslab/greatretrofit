#!/usr/bin/env python3
"""Parameter sweep runner for v1 and v2 models."""
import argparse
import numpy as np
import pandas as pd
from pathlib import Path

from retrofit_v1 import Params as V1Params, run_simulation as run_v1
from retrofit_v2 import Params as V2Params, run_simulation as run_v2


def run_v1_sweep(param_grid, n_runs=10, output_path=None):
    """Run parameter sweep for v1 model."""
    results = []

    for params_dict in param_grid:
        base_params = {k: v for k, v in params_dict.items() if not k.startswith('v2_') and k != 'seed'}

        for run in range(n_runs):
            seed = params_dict.get('seed', 42) + run * 1000
            p = V1Params(**base_params, seed=seed)
            r = run_v1(p)

            results.append({
                'version': 'v1',
                'run': run,
                'seed': seed,
                'n': p.n,
                'n_co_ops': p.n_co_ops,
                'E': p.E,
                'tau': p.tau,
                'surplus': p.surplus,
                'mean_time': p.mean_time,
                'time_var': p.time_var,
                'week_cost': p.week_cost,
                'finished': r.finished,
                'total_weeks': r.total_weeks,
                'final_total_accounts': r.final_total_accounts,
                'peak_queued': max(r.weekly_queued) if len(r.weekly_queued) > 0 else 0,
                'peak_in_progress': max(r.weekly_in_progress) if len(r.weekly_in_progress) > 0 else 0,
            })

    df = pd.DataFrame(results)
    if output_path:
        df.to_csv(output_path, index=False)
        print(f"Saved v1 sweep results to {output_path}")
    return df


def run_v2_sweep(param_grid, n_runs=10, output_path=None):
    """Run parameter sweep for v2 model."""
    results = []

    for params_dict in param_grid:
        # Separate v2 params
        base_params = {}
        v2_params = {}
        for k, v in params_dict.items():
            if k.startswith('v2_'):
                v2_params[k[3:]] = v  # Strip 'v2_' prefix
            elif k != 'seed':
                base_params[k] = v

        for run in range(n_runs):
            seed = params_dict.get('seed', 42) + run * 1000
            p = V2Params(**base_params, seed=seed, **v2_params)
            r = run_v2(p)

            results.append({
                'version': 'v2',
                'run': run,
                'seed': seed,
                'n': p.n,
                'n_co_ops': p.n_co_ops,
                'E': p.E,
                'tau': p.tau,
                'surplus': p.surplus,
                'mean_time': p.mean_time,
                'time_var': p.time_var,
                'week_cost': p.week_cost,
                'n_households': p.n_households,
                'income_mean': p.income_mean,
                'income_cv': p.income_cv,
                'wealth_pareto_alpha': p.wealth_pareto_alpha,
                'aspiration_mean': p.aspiration_mean,
                'aspiration_sd': p.aspiration_sd,
                'search_length': p.search_length,
                'n_neighbourhoods': p.n_neighbourhoods,
                'enable_bargaining': p.enable_bargaining,
                'n_banks': p.n_banks,
                'enable_default': p.enable_default,
                'income_ar1_rho': p.income_ar1_rho,
                'enable_investors': p.enable_investors,
                'enable_construction': p.enable_construction,
                'enable_demographics': p.enable_demographics,
                'finished': r.finished,
                'total_weeks': r.total_weeks,
                'final_total_accounts': r.final_total_accounts,
                'gini_wealth': r.gini_wealth,
                'price_dispersion': r.price_dispersion,
                'price_dispersion_within': r.price_dispersion_within,
                'price_dispersion_between': r.price_dispersion_between,
                'cash_buyer_share': r.cash_buyer_share,
                'time_on_market_spread': r.time_on_market_spread,
                'bank_losses': r.bank_losses,
                'default_count': r.default_count,
                'total_loan_volume': r.total_loan_volume,
                'investor_purchases': r.investor_purchases,
                'new_construction_count': r.new_construction_count,
                'peak_queued': max(r.weekly_queued) if len(r.weekly_queued) > 0 else 0,
                'peak_in_progress': max(r.weekly_in_progress) if len(r.weekly_in_progress) > 0 else 0,
            })

    df = pd.DataFrame(results)
    if output_path:
        df.to_csv(output_path, index=False)
        print(f"Saved v2 sweep results to {output_path}")
    return df


def main():
    parser = argparse.ArgumentParser(description='Run parameter sweeps for retrofit models')
    parser.add_argument('--version', choices=['v1', 'v2', 'both'], default='both',
                        help='Which model version to run')
    parser.add_argument('--out', type=str, default=None, help='Output CSV path')
    parser.add_argument('--runs', type=int, default=5, help='Number of runs per parameter set')
    parser.add_argument('--quick', action='store_true', help='Quick test sweep (fewer params)')
    args = parser.parse_args()

    # Define parameter grids
    if args.quick:
        v1_grid = [
            {'n': 1000, 'n_co_ops': 5, 'E': 100000, 'tau': 20, 'surplus': 0.2,
             'mean_time': 12, 'time_var': 4, 'week_cost': 1000, 'run_time': 2000, 'seed': 42},
            {'n': 1000, 'n_co_ops': 10, 'E': 100000, 'tau': 20, 'surplus': 0.2,
             'mean_time': 12, 'time_var': 4, 'week_cost': 1000, 'run_time': 2000, 'seed': 42},
        ]
        v2_grid = [
            {'n': 1000, 'n_co_ops': 5, 'E': 100000, 'tau': 20, 'surplus': 0.2,
             'mean_time': 12, 'time_var': 4, 'week_cost': 1000, 'run_time': 2000, 'seed': 42,
             'n_households': 1000, 'income_mean': 45000, 'income_cv': 0.35,
             'wealth_pareto_alpha': 1.5, 'aspiration_mean': 50, 'aspiration_sd': 15,
             'v2_search_length': 5, 'v2_n_neighbourhoods': 4,
             'v2_enable_bargaining': True, 'v2_n_banks': 3, 'v2_enable_default': True},
            {'n': 1000, 'n_co_ops': 10, 'E': 100000, 'tau': 20, 'surplus': 0.2,
             'mean_time': 12, 'time_var': 4, 'week_cost': 1000, 'run_time': 2000, 'seed': 42,
             'n_households': 1000, 'income_mean': 45000, 'income_cv': 0.35,
             'wealth_pareto_alpha': 1.5, 'aspiration_mean': 50, 'aspiration_sd': 15,
             'v2_search_length': 5, 'v2_n_neighbourhoods': 4,
             'v2_enable_bargaining': True, 'v2_n_banks': 3, 'v2_enable_default': True},
        ]
    else:
        # Full sweep: n_co_ops sweep like original notebook
        v1_grid = []
        for n_coops in [1, 5, 10, 25, 50, 100, 200]:
            v1_grid.append({
                'n': 100000, 'n_co_ops': n_coops, 'E': 100000, 'tau': 100, 'surplus': 0.2,
                'mean_time': 12, 'time_var': 4, 'week_cost': 1000, 'run_time': 5200, 'seed': 42
            })

        v2_grid = []
        for n_coops in [1, 5, 10, 25, 50, 100, 200]:
            v2_grid.append({
                'n': 100000, 'n_co_ops': n_coops, 'E': 100000, 'tau': 100, 'surplus': 0.2,
                'mean_time': 12, 'time_var': 4, 'week_cost': 1000, 'run_time': 5200, 'seed': 42,
                'n_households': 100000, 'income_mean': 45000, 'income_cv': 0.35,
                'wealth_pareto_alpha': 1.5, 'aspiration_mean': 50, 'aspiration_sd': 15,
                'v2_search_length': 5, 'v2_n_neighbourhoods': 10,
                'v2_enable_bargaining': True, 'v2_n_banks': 5, 'v2_enable_default': True,
                'v2_income_ar1_rho': 0.95, 'v2_income_shock_sd': 0.1, 'v2_unemployment_prob': 0.001,
                'v2_enable_investors': True, 'v2_enable_construction': True, 'v2_enable_demographics': True,
            })

    out_path = Path(args.out) if args.out else None

    if args.version in ['v1', 'both']:
        print("Running v1 sweep...")
        v1_out = out_path.with_suffix('.v1.csv') if out_path else Path('data/v1_sweep.csv')
        v1_out.parent.mkdir(parents=True, exist_ok=True)
        run_v1_sweep(v1_grid, n_runs=args.runs, output_path=v1_out)

    if args.version in ['v2', 'both']:
        print("Running v2 sweep...")
        v2_out = out_path.with_suffix('.v2.csv') if out_path else Path('data/v2_sweep.csv')
        v2_out.parent.mkdir(parents=True, exist_ok=True)
        run_v2_sweep(v2_grid, n_runs=args.runs, output_path=v2_out)

    print("Sweep complete!")


if __name__ == '__main__':
    main()