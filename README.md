# The Great Retrofit: Housing Retrofit Co-op Simulation Models

A simulation of **housing retrofit cooperatives** (Brussels context): buildings that need energy retrofit are queued, assigned to retrofit co-ops, financed, and completed, while households, banks, investors and demographics interact over a weekly time axis. Two versions are provided: **v1** (baseline queueing-financial model) and **v2** (full agent-based model).

Contributing models: **Nvidia Nemotron 3 Ultra** and **Beam 1.0**.

---

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

---

## Repository Layout

```
TheGreatRetrofit/
├── v1/                      # Original queueing-financial model
│   ├── src/retrofit_v1/     # Core package (model, params, results, common/)
│   ├── test_v1/             # Tests
│   └── docs/                # v1 documentation
├── v2/                      # Full agent-based model
│   ├── src/retrofit_v2/     # Core package (8 modules + common/)
│   ├── test_v2/             # Tests + snapshots
│   ├── docs/                # v2 documentation
│   └── TheGreatRetrofit_v2.ipynb   # Exploratory notebook (documented, charts)
├── v1v2testcomparison/      # Cross-version comparison artefacts
├── scripts/                 # Parameter sweeps & plotting
├── docs/                    # Comparison report & plans
├── data/                    # Generated sweep outputs (gitignored *.csv/*.json)
├── Joffa's original/        # Original prototype notebook & docs
└── pyproject.toml
```

---

## Quick Start

```bash
# Install (editable, with dev deps)
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

Notes:
- Import paths assume the package is installed (`pip install -e .`) so `retrofit_v1` / `retrofit_v2` are importable. Alternatively set `PYTHONPATH` to `v1/src` and `v2/src`.
- All time series in `Result` are indexed by **weeks**.

---

## Run Tests

```bash
# All tests (53)
pytest v1/test_v1/ v2/test_v2/ -v

# v1 only
pytest v1/test_v1/ -v

# v2 only
pytest v2/test_v2/ -v
```

---

## Parameter Sweeps

```bash
# Quick sweeps (both versions)
python scripts/run_sweep.py --quick --version both --out data/sweep.csv

# Full sweeps
python scripts/run_sweep.py --version both --out data/sweep.csv

# Plot results
python scripts/plot_results.py --v1 data/sweep.v1.csv --v2 data/sweep.v2.csv --out plots/
```

---

## Documentation

| Document | Location |
|----------|----------|
| v1 Documentation | `v1/docs/v1_documentation.md` |
| v2 Documentation | `v2/docs/v2_documentation.md` |
| Comparison Report | `docs/comparison_report.md` |
| Implementation Plan | `docs/plans/2026-11-03-model-upgrade.md` |
| Upgrade Plan (original) | `Joffa's original/upgrade plan.md` |
| v2 Notebook | `v2/TheGreatRetrofit_v2.ipynb` |

---

## v2 Mechanisms (summary)

1. Limited search — households see `search_length` random co-ops.
2. Bargaining — buyers bid below asking; sellers have a reservation price.
3. Bank lending — co-ops borrow for ~50% of projects; payment-to-income cap 30%.
4. Default & foreclosure — banks check solvency, absorb losses (50% recovery).
5. Local demand — time-on-market tracked per neighbourhood.
6. Income process — AR(1) log-income + unemployment spells.
7. Investor market — landlords buy when yield + growth > hurdle rate.
8. Demographics — births/deaths, inheritance of buildings.
9. Depreciation — buildings degrade; retrofitted degrade slower.
10. Construction — new buildings when price > 1.2× build cost.

---

## Original Prototype

The original prototype notebook and docs live in `Joffa's original/` (`GreatRetroFit.ipynb`, `Model_Documentation.md`).
