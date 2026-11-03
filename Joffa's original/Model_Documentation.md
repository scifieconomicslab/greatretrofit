# The Great Retrofit: Housing Co-op Retrofit Model Documentation

## Overview

**The Great Retrofit** is an agent-based simulation model that explores how housing retrofit cooperatives (co-ops) in Brussels could collectively finance and execute energy-efficiency renovations on a large scale. The model simulates a system where buildings needing retrofits request work, get assigned to co-ops with available budget capacity, and the co-ops progressively complete projects while managing their finances.

Joffa's original name for this python notebook was GreatRetroFitv2.ipynb, but I've renamed it here to prevent confusion. This is the original.

---

## The Real-World Problem Being Modeled

Brussels has a massive stock of older buildings that need energy-efficiency upgrades (insulation, heat pumps, new windows, etc.) to meet climate targets. Individual homeowners often can't afford the upfront cost. The **retrofit co-op** idea: groups pool money into a shared fund, use it to finance retrofits on member buildings, and get repaid (with a small surplus) over time — creating a revolving fund that grows and can tackle more buildings.

This model tests: *Given a certain number of co-ops with a starting endowment, how fast can they retrofit a large building stock? What parameters matter most?*

---

## Core Concepts

### Four Lists (States) for Buildings

Every building in the simulation exists in exactly one of four lists at any time:

| List | Meaning |
|------|---------|
| **to_do** | Buildings that still need a retrofit but haven't requested one yet |
| **queued** | Buildings that have requested a retrofit and are waiting to be assigned to a co-op |
| **projects** (per co-op) | Buildings currently being worked on by a specific co-op |
| **finished** | Buildings whose retrofits are complete |

Buildings flow in one direction: `to_do → queued → projects → finished`

### Co-ops as Financial Engines

Each co-op has:
- **An account balance** (starts with an endowment `E`)
- **A project list** (buildings currently under construction)
- **A budget constraint**: It can only take on a new project if its current account balance can cover the *estimated total cost* of all its ongoing projects *plus* the new one

Co-ops earn money by completing projects: they get back the project's cost **plus a surplus percentage** (e.g., 20%). This surplus is the "profit" that lets the fund grow.

---

## How the Simulation Runs (Step by Step)

The model runs in **weekly time steps** for up to `run_time` weeks (default: 100 years = 5,200 weeks). Each week, three things happen in order:

### 1. Buildings Decide to Request Retrofits
- From the `to_do` list, a random number of buildings "decide" to start the process
- The number is drawn from a **Poisson distribution** with mean `tau` (average requests per week)
- But it can't exceed how many buildings are left in `to_do`
- These buildings move from `to_do` → `queued`

### 2. Queued Buildings Get Assigned to Co-ops
- The model goes through each building in `queued` (in order)
- For each building, it calculates the **retrofit cost estimate** (based on that building's randomly assigned duration × weekly cost)
- It finds all co-ops that have **enough money in their account** to cover this new project *on top of* their existing commitments
- If at least one co-op qualifies, one is chosen **at random** from the eligible ones
- The building moves from `queued` → that co-op's `projects` list
- If **no co-op** has capacity, the assignment loop stops (remaining queued buildings wait for next week)

### 3. Co-Ops Do Work on Their Projects
- For each co-op, for each project in its list:
  - **If the project's remaining time is 0**: The retrofit is done!
    - Building moves to `finished`
    - Co-op's account **increases** by `(1 + surplus) × project_cost`
    - Project removed from co-op's list
  - **If the project still needs time**:
    - Co-op **spends `week_cost`** from its account
    - Project's remaining time **decreases by 1 week**
    - (But only if the co-op has at least `week_cost` in its account — otherwise work pauses)

### 4. Record Keeping
- After each week, the model records:
  - Counts in each list (`to_do`, `queued`, `in_progress`, `finished`)
  - Total money across all co-op accounts
  - Current week number

The simulation stops early if **all buildings are finished**.

---

## All Parameters and Variables

### Global Simulation Parameters (Set Before Each Run)

| Symbol | Name | Default Value | Description |
|--------|------|---------------|-------------|
| `runs` | Number of Monte Carlo runs | 10 | How many times to repeat the simulation with different random seeds (for statistical robustness) |
| `n` | Total buildings to retrofit | 100,000 | Size of the building stock needing upgrades |
| `mean_time` | Mean retrofit duration | 12 weeks | Average time a retrofit takes |
| `time_var` | Retrofit duration variance | 4 weeks | Spread around the mean (actual time = mean ± uniform[0, 2×time_var]) |
| `week_cost` | Weekly cost per project | €1,000 | Money a co-op spends per week per active project |
| `run_time` | Maximum simulation time | 5,200 weeks (100 years) | Hard cap on how long the simulation runs |
| `tau` | Mean weekly request rate | 100 | Poisson mean for how many buildings request retrofits per week |
| `n_co_ops` | Number of co-ops | 100 (varied in experiments) | How many independent retrofit cooperatives exist |
| `surplus` | Co-op surplus rate | 0.20 (20%) | Percentage markup co-ops earn on completed projects |
| `E` | Initial endowment per co-op | €100,000 | Starting capital in each co-op's account |

### Per-Building Attributes (Randomly Assigned at Start)

| Variable | How It's Generated | Role |
|----------|-------------------|------|
| `times[b]` | `mean_time + uniform(-time_var, +time_var)` | Total weeks needed for building `b`'s retrofit |
| `costs[b]` | `week_cost × times[b]` | Total cost of building `b`'s retrofit |

These are fixed at initialization and don't change during the run.

### Per-Co-op State Variables (Updated Each Week)

| Variable | Description |
|----------|-------------|
| `accounts[c]` | Current euro balance of co-op `c` |
| `projects[c]` | List of building IDs currently assigned to co-op `c` |

### Weekly Tracking Variables (Recorded for Analysis)

| Variable | Description |
|----------|-------------|
| `len(to_do)` | Buildings not yet requesting retrofit |
| `len(queued)` | Buildings waiting for co-op assignment |
| `len(with_capacity)` | Number of co-ops that could afford the *current* queued building (during assignment loop) |
| `len([b for c in projects for b in c])` | Total buildings **in progress** across all co-ops |
| `len(finished)` | Buildings completed |
| `t` | Current week number |
| `sum(accounts)` | Total capital across all co-ops |

---

## Key Dynamics and Insights

### 1. **The Bottleneck is Co-op Capital, Not Labour**
The model explicitly assumes "labour is unlimited" — the only constraint is whether a co-op has enough *money* to take on a new project. This makes it a **financial flow model**, not a workforce model.

### 2. **Surplus Drives Growth**
Without surplus (`surplus = 0`), co-ops would just break even on each project and their total capital would stay flat at `n_co_ops × E`. The 20% surplus means each completed project grows the co-op's account, enabling it to take on *more* projects over time — a compounding effect.

### 3. **Request Rate (tau) vs. Processing Capacity**
- If `tau` is too high: `queued` builds up, co-ops get overwhelmed, buildings wait longer
- If `tau` is too low: Co-ops sit idle with money that could be deployed
- The model explores this tension

### 4. **Number of Co-ops (n_co_ops) Matters**
More co-ops = more parallel processing capacity, but each starts with the same endowment `E`, so total initial capital = `n_co_ops × E`. The experiments in the notebook sweep `n_co_ops` from 1 to 200 to see the effect.

### 5. **Random Duration Creates Heterogeneity**
Buildings don't all take the same time. Some finish in ~8 weeks, others take ~16 weeks. This means co-ops' cash flows are staggered — they don't all get paid at once.

---

## What the Model Does NOT Include (Yet)

The `upgrade plan.md` file lists many planned extensions. The current model is deliberately simple. Missing elements include:

- **Household-level decisions**: No individual homeowners with incomes, savings, or preferences
- **Bargaining/negotiation**: Fixed pricing, no below-ask offers or reservation prices
- **Neighbourhood geography**: No spatial structure, no local demand hotspots
- **Credit markets**: No banks, mortgages, LTV limits, interest rates, or default risk
- **Building heterogeneity**: All buildings differ only in retrofit duration, not size, age, location, or type
- **Demographic dynamics**: No births, deaths, household formation, inheritance
- **Macro shocks**: No interest rate changes, income shocks, or policy interventions
- **Investor/landlord market**: No buy-to-let logic, rental yields, or speculative demand

---

## Experimental Design in the Notebook

The notebook runs a **parameter sweep** over `n_co_ops`:
```python
for n_coops in [1, 10, 25, 50, 75, 100, 200]:
    for r in range(runs):  # 10 runs each
        # run simulation, collect step_results
```

This produces a dataset (`results_E100k_n100k_ncsweep_tau100_steps_v2.csv`) with weekly snapshots for every run, enabling analysis of:
- How fast the system finishes vs. number of co-ops
- Account balance trajectories (do co-ops go bankrupt? grow unbounded?)
- Queue dynamics (backlogs, clearance times)
- Variability across random seeds

---

## Visual Outputs

The notebook generates two main plots:

1. **Stacked area / line chart** of building counts over time:
   - `to_do` (pink) — shrinks as buildings request retrofits
   - `queued` (orange) — builds up then drains
   - `in_progress` (blue) — peaks then declines
   - `finished` (red) — grows to `n`

2. **Total co-op accounts over time** (green line):
   - Shows whether the collective fund grows, shrinks, or stabilizes

---

## How to Interpret Results

| Observation | Likely Meaning |
|-------------|----------------|
| `finished` reaches `n` quickly | System has enough capital & throughput |
| `queued` stays high for a long time | Bottleneck: not enough co-op capital to assign projects |
| `accounts` grows steadily | Surplus is working; fund is compounding |
| `accounts` dips negative (impossible here) | Would mean co-ops spent money they didn't have — prevented by the `if accounts[c] >= week_cost` check |
| High variance across runs | System is sensitive to random timing of requests / durations |

---

## Potential Questions This Model Can Answer

1. **Minimum viable co-op count**: How many co-ops (with €100k each) are needed to retrofit 100k buildings in X years?
2. **Endowment sensitivity**: What if `E = €50k` vs. `€200k`?
3. **Surplus sensitivity**: Is 10% surplus enough? What about 30%?
4. **Request rate calibration**: What `tau` matches real-world homeowner decision-making?
5. **Policy simulation**: What happens if government adds a one-time grant to all co-op accounts in year 5?

---

## Running the Model Yourself

The model is in `GreatRetroFitV2.ipynb` — a Jupyter notebook. To run it:

1. Open the notebook in Jupyter/VS Code
2. Run cells top to bottom
3. The key simulation loop is in the long code cell (execution_count 36)
4. Results are saved to CSV for further analysis
5. Plots are generated in the last two code cells

To modify parameters, change the values in the "Model parameters" cell (execution_count 35).

---

## Summary

**The Great Retrofit (current version)** is a **queueing-financial model** of retrofit cooperatives. It strips away household behaviour, geography, credit markets, and building diversity to focus on one core question:

> *Given a pool of capital distributed across N co-ops, earning a surplus on each completed retrofit, how fast can the system process a large stock of buildings?*

It's a **foundational layer** — the `upgrade plan.md` shows the rich, realistic housing market model the authors intend to build on top of this core engine.

---

*Document generated from analysis of `GreatRetroFitV2.ipynb` and `upgrade plan.md`*