# v1 Retrofit Co-op Model Documentation

## Overview

The v1 model is a **queueing-financial simulation** of retrofit cooperatives in Brussels. It models a system where buildings needing energy-efficiency upgrades request work, get assigned to co-ops with available budget capacity, and co-ops progressively complete projects while managing their finances through a revolving fund with surplus.

This version is a direct, faithful translation of the original `GreatRetroFitV2.ipynb` notebook into a clean, tested Python package.

---

## Core Concepts

### Building States (Four Lists)

Every building exists in exactly one of four lists:

| List | Description |
|------|-------------|
| `to_do` | Buildings needing retrofit but haven't requested yet |
| `queued` | Buildings that requested retrofit, awaiting co-op assignment |
| `projects` (per co-op) | Buildings currently under construction by a co-op |
| `finished` | Buildings with completed retrofits |

**Flow:** `to_do → queued → projects → finished` (one direction only)

### Co-ops as Financial Engines

Each co-op has:
- **Account balance** (starts at endowment `E`)
- **Project list** (buildings currently under construction)
- **Budget constraint**: Can only take a new project if `account ≥ sum(estimated_cost of all current projects) + estimated_cost of new project`

**Revenue model**: On completion, co-op receives `(1 + surplus) × project_cost` — the surplus (e.g., 20%) grows the fund.

---

## Simulation Loop (Weekly Time Steps)

The model runs in discrete weekly steps for up to `run_time` weeks.

### Week `t` Operations (in order):

#### 1. Buildings Request Retrofits
```python
if to_do:
    n_requests = min(Poisson(tau), len(to_do))
    selected = random_choice(to_do, n_requests, replace=False)
    queued.extend(selected)
    to_do = to_do - selected
```

#### 2. Assign Queued Buildings to Co-ops
```python
for building in queued.copy():
    estimate = cost[building]
    with_capacity = [c for c in coops
                     if sum(time[p]*week_cost for p in projects[c]) + estimate <= accounts[c]]
    if not with_capacity:
        break  # remaining queued buildings wait for next week
    c = random_choice(with_capacity)
    projects[c].append(queued.pop(0))
```

#### 3. Co-Ops Execute Work
```python
for each co-op c:
    for each project p in projects[c] (copy):
        if time[p] == 0:
            # Complete
            projects[c].remove(p)
            finished.append(p)
            accounts[c] += (1 + surplus) * cost[p]
        else:
            # Work in progress
            if accounts[c] >= week_cost:
                time[p] -= 1
                accounts[c] -= week_cost
```

#### 4. Record State
All list lengths, total accounts, and co-ops with capacity are recorded.

**Early termination**: If `len(finished) == n`, simulation stops.

---

## Parameters

| Symbol | Name | Type | Default | Description |
|--------|------|------|---------|-------------|
| `n` | Total buildings | int | 100,000 | Buildings needing retrofit |
| `n_co_ops` | Number of co-ops | int | 100 | Independent retrofit cooperatives |
| `E` | Endowment per co-op | float | 100,000 | Starting capital (€) |
| `tau` | Request rate | float | 100 | Mean weekly requests (Poisson) |
| `surplus` | Surplus rate | float | 0.20 | Markup on completed projects (20%) |
| `mean_time` | Mean duration | float | 12 | Average retrofit weeks |
| `time_var` | Duration variance | float | 4 | Uniform range ±time_var around mean |
| `week_cost` | Weekly cost | float | 1,000 | Cost per active project per week (€) |
| `run_time` | Max weeks | int | 5,200 | Simulation horizon (100 years) |
| `seed` | Random seed | int | None | Reproducibility |

### Per-Building Attributes (Random, Fixed at Init)

| Variable | Generation | Role |
|----------|------------|------|
| `times[b]` | `mean_time + Uniform(-time_var, +time_var)` | Weeks needed for building `b` |
| `costs[b]` | `week_cost × times[b]` | Total cost for building `b` |

---

## Outputs (Result Object)

| Field | Type | Description |
|-------|------|-------------|
| `weekly_to_do` | `np.ndarray[int]` | Buildings in `to_do` per week |
| `weekly_queued` | `np.ndarray[int]` | Buildings in `queued` per week |
| `weekly_in_progress` | `np.ndarray[int]` | Buildings in `projects` per week |
| `weekly_finished` | `np.ndarray[int]` | Cumulative finished per week |
| `weekly_total_accounts` | `np.ndarray[float]` | Sum of all co-op accounts per week |
| `weekly_with_capacity` | `np.ndarray[int]` | Co-ops able to take current queued building |
| `finished` | `int` | Total completed at end |
| `total_weeks` | `int` | Weeks simulated |
| `final_total_accounts` | `float` | Total capital at end |
| `params` | `Params` | Parameters used (for traceability) |

---

## Invariants (Guaranteed by Design)

| Invariant | Test |
|-----------|------|
| Mass conservation: `to_do + queued + in_progress + finished = n` every week | `test_mass_conservation` |
| `finished` monotonic non-decreasing | `test_finished_monotonic` |
| `to_do` monotonic non-increasing | `test_to_do_monotonic_decrease` |
| All counts ≥ 0 | `test_*_nonnegative` |
| Total accounts ≥ 0 (work pauses if insufficient funds) | `test_total_accounts_nonnegative` |
| `finished ≤ n` always | `test_finished_bounded_by_n` |
| Same seed → identical trajectories | `test_seed_reproducibility` |
| Capital grows with surplus > 0 (if completes) | `test_surplus_grows_capital` |

---

## Key Dynamics

### 1. Capital is the Only Bottleneck
Labour is assumed unlimited. The sole constraint is whether a co-op has enough money to cover the **full estimated cost** of all its current + new projects.

### 2. Surplus Drives Compounding Growth
- Without surplus: Total capital = `n_co_ops × E` forever (break-even)
- With surplus: Each completed project returns `cost × (1+surplus)`, growing the fund → more parallel projects → faster completion

### 3. Request Rate vs. Processing Capacity
- High `tau` → queue builds up, co-ops overwhelmed
- Low `tau` → co-ops idle, capital underutilized
- Balance determines system throughput

### 4. Heterogeneous Durations Stagger Cash Flows
Buildings take 8–16 weeks (with defaults). Co-ops don't all get paid at once, creating natural cash flow smoothing.

---

## Running the Model

```python
from retrofit_v1 import Params, run_simulation

params = Params(
    n=100000,
    n_co_ops=100,
    E=100000,
    tau=100,
    surplus=0.2,
    mean_time=12,
    time_var=4,
    week_cost=1000,
    run_time=5200,
    seed=42,
)
result = run_simulation(params)

# Access results
print(f"Finished: {result.finished}/{params.n}")
print(f"Weeks: {result.total_weeks}")
print(f"Final capital: €{result.final_total_accounts:,.0f}")

# Plot time series
import matplotlib.pyplot as plt
plt.plot(result.weekly_finished, label='Finished')
plt.plot(result.weekly_queued, label='Queued')
plt.plot(result.weekly_in_progress, label='In Progress')
plt.legend()
plt.show()
```

---

## Parameter Sweeps

The original notebook sweeps `n_co_ops`:

```python
for n_coops in [1, 10, 25, 50, 75, 100, 200]:
    for run in range(10):
        params = Params(n=100000, n_co_ops=n_coops, E=100000, ...)
        result = run_simulation(params)
        # collect results
```

See `scripts/run_sweep.py` for a ready-to-use sweep script.

---

## Comparison with Notebook

This package reproduces the exact logic from `GreatRetroFitV2.ipynb`:
- Same random number generation (NumPy Generator with seed)
- Same Poisson request process
- Same assignment logic (first-come, first-served; random eligible co-op)
- Same work execution (sequential within co-op, parallel across co-ops)
- Same surplus calculation
- Same recording

**Differences:**
- Clean parameter validation via dataclass
- Structured Result object instead of raw lists
- Comprehensive test suite
- No matplotlib/seaborn dependency in core (optional for plotting)
- Modular, importable package structure

---

## Limitations (Addressed in v2)

| Limitation | v2 Plan |
|------------|---------|
| No household-level decisions | Households with aspiration, affordability, capital |
| No building heterogeneity beyond duration | Size, age, location attributes |
| No search friction | Limited search length per household |
| No bargaining | Bid below asking, seller reservation price |
| No geography | Neighbourhoods with local demand |
| No credit markets | Banks with LTV, spreads, default |
| No demographics | Births, deaths, inheritance, income shocks |
| No investor market | Landlords buying for rental yield |
| No stock evolution | Depreciation, construction, demolition |
| Limited monitors | Gini, price dispersion, cash buyers, time-on-market spread |

See `docs/v2_documentation.md` and `docs/comparison_report.md` for v2 details.