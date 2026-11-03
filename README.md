# The Great Retrofit: Housing Co-op Simulation Models

Two versions of a simulation model for housing retrofit cooperatives in Brussels:

## Version Comparison

| Aspect | v1 (Baseline) | v2 (Full Agent-Based) |
|--------|---------------|----------------------|
| **Paradigm** | Queueing-financial | Agent-based |
| **Lines of code** | ~300 | ~2,500 |
| **Agents** | Buildings, Co-ops | Households, Buildings, Co-ops, Banks |
| **Heterogeneity** | Duration only | Income, wealth, aspiration, tastes, building attrs |
| **Finance** | Self-funded co-ops | Bank lending, bargaining, default |
| **Space** | Single market | Neighbourhoods with local demand |
| **Dynamics** | Static stock | Demographics, depreciation, construction |
| **Monitors** | Queue lengths, capital | Gini, price dispersion, TOM, bank losses, etc. |

## Quick Start

```bash
# Install
pip install -e .[dev]

# Run v1 (baseline)
python -c "
from retrofit_v1 import Params, run_simulation
p = Params(n=1000, n_co_ops=10, E=100000, tau=20, surplus=0.2, seed=42)
r = run_simulation(p)
print(f'v1: {r.finished}/{p.n} buildings in {r.total_weeks} weeks')
"

# Run v2 (full model)
python -c "
from retrofit_v2 import Params, run_simulation
p = Params(n=1000, n_co_ops=10, E=100000, tau=20, surplus=0.2, seed=42,
           n_households=1000, income_mean=45000, income_cv=0.35,
           wealth_pareto_alpha=1.5, aspiration_mean=50, aspiration_sd=15,
           search_length=5, n_neighbourhoods=10,
           enable_bargaining=True, n_banks=5, enable_default=True,
           income_ar1_rho=0.95, income_shock_sd=0.1, unemployment_prob=0.001,
           enable_investors=True, enable_construction=True, enable_demographics=True)
r = run_simulation(p)
print(f'v2: {r.finished}/{p.n} buildings, Gini={r.gini_wealth:.3f}')
"
```

## Run Tests

```bash
# All tests (53 tests)
pytest v1/test_v1/ v2/test_v2/ -v

# v1 only (22 tests)
pytest v1/test_v1/ -v

# v2 only (31 tests)
pytest v2/test_v2/ -v
```

## Parameter Sweeps

```bash
# Quick sweeps
python scripts/run_sweep.py --quick --version both --out data/sweep.csv

# Full sweeps (like original notebook)
python scripts/run_sweep.py --version both --out data/sweep.csv

# Plot results
python scripts/plot_results.py --v1 data/sweep.v1.csv --v2 data/sweep.v2.csv --out plots/
```

## Documentation

| Document | Location |
|----------|----------|
| v1 Documentation | `v1/docs/v1_documentation.md` |
| v2 Documentation | `v2/docs/v2_documentation.md` |
| Comparison Report | `docs/comparison_report.md` |
| Implementation Plan | `docs/plans/2026-11-03-model-upgrade.md` |
| Upgrade Plan (original) | `upgrade plan.md` |

## Project Structure

```
TheGreatRetrofit/
├── v1/                      # Original queueing-financial model
│   ├── src/retrofit_v1/     # Core package
│   ├── test_v1/             # Tests (22)
│   └── docs/
├── v2/                      # Full agent-based model
│   ├── src/retrofit_v2/     # Core package (8 modules)
│   ├── test_v2/             # Tests (31)
│   └── docs/
├── common/                  # Shared utilities
├── scripts/                 # Sweep & plotting
├── docs/                    # Comparison & plans
├── data/                    # Output CSV files
└── pyproject.toml
```

## Upgrade Plan Traceability

All 23 items from `upgrade plan.md` implemented in v2:

1. ✅ Aspiration trait (persistent per household)
2. ✅ Affordability heterogeneity (truncated normal)
3. ✅ Wealth ~ Pareto independent of income
4. ✅ Limited search length
5. ✅ Building attributes (size, age, location)
6. ✅ Household taste weights + shocks
7. ✅ Bargaining (bid below asking, reservation price)
8. ✅ Local demand signals (per-neighbourhood TOM)
9. ✅ Exit hazard (age/income/stress dependent)
10. ✅ Income process (AR(1) + unemployment)
11. ✅ Demographics (births, deaths, inheritance)
12. ✅ Consumption/capital dynamics
13. ✅ Bank heterogeneity (LTV, spreads)
14. ✅ Borrower-dependent lending (PTI cap, risk premium)
15. ✅ Default & foreclosure
16. ✅ Bank adaptation
17. ✅ Heterogeneous expectations
18. ✅ Investor/landlord market
19. ✅ Transaction costs
20. ✅ Stock evolution (depreciation, construction)
21. ✅ Macro shocks (time-varying rates, income)
22. ✅ Gini monitor
23. ✅ Price dispersion, cash buyers, TOM spread monitors

## Original Notebook

The original prototype: `GreatRetroFitV2.ipynb`