#!/usr/bin/env python3
"""Plotting script for sweep results."""
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (10, 6)


def plot_v1_sweep(csv_path):
    """Plot v1 sweep results."""
    df = pd.read_csv(csv_path)

    # Summary stats per parameter set
    summary = df.groupby(['n_co_ops', 'n', 'E', 'tau', 'surplus']).agg(
        mean_weeks=('total_weeks', 'mean'),
        std_weeks=('total_weeks', 'std'),
        mean_final_accounts=('final_total_accounts', 'mean'),
        completion_rate=('finished', lambda x: (x == df.loc[x.index, 'n']).mean()),
        mean_peak_queued=('peak_queued', 'mean'),
    ).reset_index()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Weeks to completion vs n_co_ops
    ax = axes[0, 0]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.errorbar(sub['n_co_ops'], sub['mean_weeks'], yerr=sub['std_weeks'],
                    marker='o', label=f'n={n}', capsize=3)
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Mean Weeks to Completion')
    ax.set_title('v1: Completion Time vs Co-op Count')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Final capital vs n_co_ops
    ax = axes[0, 1]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['mean_final_accounts'] / 1e6, marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Final Capital (€M)')
    ax.set_title('v1: Final Capital vs Co-op Count')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Completion rate
    ax = axes[1, 0]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['completion_rate'], marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Completion Rate')
    ax.set_title('v1: Fraction of Runs Completing All Buildings')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Peak queue
    ax = axes[1, 1]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['mean_peak_queued'], marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Peak Queued Buildings')
    ax.set_title('v1: Maximum Queue Backlog')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_v2_sweep(csv_path):
    """Plot v2 sweep results."""
    df = pd.read_csv(csv_path)

    summary = df.groupby(['n_co_ops', 'n', 'E', 'tau', 'surplus',
                          'n_households', 'n_neighbourhoods',
                          'enable_bargaining', 'n_banks', 'enable_default']).agg(
        mean_weeks=('total_weeks', 'mean'),
        std_weeks=('total_weeks', 'std'),
        mean_final_accounts=('final_total_accounts', 'mean'),
        mean_gini=('gini_wealth', 'mean'),
        mean_price_disp_between=('price_dispersion_between', 'mean'),
        mean_cash_share=('cash_buyer_share', 'mean'),
        mean_defaults=('default_count', 'mean'),
        completion_rate=('finished', lambda x: (x == df.loc[x.index, 'n']).mean()),
    ).reset_index()

    fig, axes = plt.subplots(3, 2, figsize=(14, 14))

    # Weeks to completion
    ax = axes[0, 0]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.errorbar(sub['n_co_ops'], sub['mean_weeks'], yerr=sub['std_weeks'],
                    marker='o', label=f'n={n}', capsize=3)
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Mean Weeks to Completion')
    ax.set_title('v2: Completion Time vs Co-op Count')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Gini wealth
    ax = axes[0, 1]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['mean_gini'], marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Mean Gini Wealth')
    ax.set_title('v2: Wealth Inequality vs Co-op Count')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Price dispersion between neighbourhoods
    ax = axes[1, 0]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['mean_price_disp_between'], marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Price Dispersion Between NH')
    ax.set_title('v2: Spatial Price Dispersion')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Cash buyer share
    ax = axes[1, 1]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['mean_cash_share'], marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Cash Buyer Share')
    ax.set_title('v2: Fraction of Non-Financed Retrofits')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Default count
    ax = axes[2, 0]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['mean_defaults'], marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Mean Defaults per Run')
    ax.set_title('v2: Bank Defaults')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Final capital
    ax = axes[2, 1]
    for n in summary['n'].unique():
        sub = summary[summary['n'] == n]
        ax.plot(sub['n_co_ops'], sub['mean_final_accounts'] / 1e6, marker='o', label=f'n={n}')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Final Capital (€M)')
    ax.set_title('v2: Final Capital vs Co-op Count')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_comparison(v1_csv, v2_csv):
    """Compare v1 vs v2 results."""
    v1_df = pd.read_csv(v1_csv)
    v2_df = pd.read_csv(v2_csv)

    # Align on n_co_ops
    v1_sum = v1_df.groupby('n_co_ops').agg(
        mean_weeks=('total_weeks', 'mean'),
        std_weeks=('total_weeks', 'std'),
        mean_final_accounts=('final_total_accounts', 'mean'),
    ).reset_index()

    v2_sum = v2_df.groupby('n_co_ops').agg(
        mean_weeks=('total_weeks', 'mean'),
        std_weeks=('total_weeks', 'std'),
        mean_final_accounts=('final_total_accounts', 'mean'),
        mean_gini=('gini_wealth', 'mean'),
    ).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Completion time comparison
    ax = axes[0]
    ax.errorbar(v1_sum['n_co_ops'], v1_sum['mean_weeks'], yerr=v1_sum['std_weeks'],
                marker='o', label='v1', capsize=3)
    ax.errorbar(v2_sum['n_co_ops'], v2_sum['mean_weeks'], yerr=v2_sum['std_weeks'],
                marker='s', label='v2', capsize=3)
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Mean Weeks to Completion')
    ax.set_title('Completion Time: v1 vs v2')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Final capital comparison
    ax = axes[1]
    ax.plot(v1_sum['n_co_ops'], v1_sum['mean_final_accounts'] / 1e6, marker='o', label='v1')
    ax.plot(v2_sum['n_co_ops'], v2_sum['mean_final_accounts'] / 1e6, marker='s', label='v2')
    ax.set_xscale('log')
    ax.set_xlabel('Number of Co-ops')
    ax.set_ylabel('Final Capital (€M)')
    ax.set_title('Final Capital: v1 vs v2')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description='Plot sweep results')
    parser.add_argument('--v1', type=str, help='Path to v1 sweep CSV')
    parser.add_argument('--v2', type=str, help='Path to v2 sweep CSV')
    parser.add_argument('--out', type=str, default=None, help='Output directory for plots')
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else Path('plots')
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.v1 and args.v2:
        print("Plotting comparison...")
        fig = plot_comparison(args.v1, args.v2)
        fig.savefig(out_dir / 'comparison.png', dpi=150)
        plt.close(fig)

    if args.v1:
        print("Plotting v1...")
        fig = plot_v1_sweep(args.v1)
        fig.savefig(out_dir / 'v1_sweep.png', dpi=150)
        plt.close(fig)

    if args.v2:
        print("Plotting v2...")
        fig = plot_v2_sweep(args.v2)
        fig.savefig(out_dir / 'v2_sweep.png', dpi=150)
        plt.close(fig)

    print(f"Plots saved to {out_dir}")


if __name__ == '__main__':
    main()