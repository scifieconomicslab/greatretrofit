# v1: Queueing-Financial Retrofit Co-op Model

## Overview

The **v1 model** is a faithful translation of the original `GreatRetroFitV2.ipynb` notebook into a clean, tested Python package. It implements a **queueing-financial simulation** of retrofit cooperatives in Brussels.

## Core Concept

Buildings needing energy-efficiency upgrades flow through four states:
```
to_do → queued → projects (per co-op) → finished
```

Co-ops are financial engines with:
- Account balance (initial endowment `E`)
- Budget constraint: can only take projects if `account ≥ sum(current project costs) + new project cost`
- Revenue: `(1 + surplus) × project_cost` on completion

## Installation

```bash
pip install -e .[dev]
```

## Running the Model

```python
from retrofit_v1 import Params, run_simulation

params = Params(
    n=100000,           # buildings needing retrofit
    n_co_ops=100,       # number of cooperatives
    E=100000,           # endowment per co-op (€)
    tau=100,            # mean weekly requests (Poisson)
    surplus=0.2,        # 20% surplus rate
    mean_time=12,       # mean retrofit duration (weeks)
    time_var=4,         # duration variance (±weeks)
    week_cost=1000,     # weekly cost per project (€)
    run_time=5200,      # max weeks (100 years)
    seed=42,            # reproducibility
)
result = run_simulation(params)

print(f"Finished: {result.finished}/{params.n}")
print(f"Weeks: {result.total_weeks}")
print(f"Final capital: €{result.final_total_accounts:,.0f}")
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n` | int | 100000 | Total buildings |
| `n_co_ops` | int | 100 | Number of co-ops |
| `E` | float | 100000 | Endowment per co-op |
| `tau` | float | 100 | Weekly request rate |
| `surplus` | float | 0.2 | Surplus rate (20%) |
| `mean_time` | float | 12 | Mean retrofit weeks |
| `time_var` | float | 4 | Duration variance |
| `week_cost` | float | 1000 | Weekly cost/project |
| `run_time` | int | 5200 | Max simulation weeks |
| `seed` | int | None | Random seed |

## Outputs (Result Object)

- `weekly_to_do`, `weekly_queued`, `weekly_in_progress`, `weekly_finished`: Time series
- `weekly_total_accounts`: Total capital across co-ops
- `weekly_with_capacity`: Co-ops able to take next project
- `finished`, `total_weeks`, `final_total_accounts`: Summary scalars

## Key Dynamics

1. **Capital is the bottleneck** — labour is unlimited
2. **Surplus drives compounding growth** — each completion grows the fund
3. **Request rate vs capacity** — high `tau` creates queues, low `tau` underutilizes co-ops
4. **Heterogeneous durations** — staggered cash flows (8-16 weeks)

## Tests

```bash
# Run v1 tests
pytest v1/test_v1/ -v

# Run invariant tests (apply to both versions)
pytest v1/test_v1/test_invariants.py -v
```

## Parameter Sweeps

```bash
# Quick sweep
python scripts/run_sweep.py --version v1 --quick --out data/v1_sweep.csv

# Full sweep (like original notebook)
python scripts/run_sweep.py --version v1 --out data/v1_sweep.csv
```

## Documentation

See `docs/v1_documentation.md` for detailed documentation.