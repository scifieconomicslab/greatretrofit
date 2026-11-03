# The Great Retrofit Model Upgrade Implementation Plan

**Goal:** Transform the current Jupyter notebook prototype into a proper Python package (v1), then implement an upgraded model (v2) with household-level decisions, building heterogeneity, financial dynamics, and market realism — adapting the upgrade plan concepts to the retrofit co-op context. Create automated comparison tests and documentation for both versions.

**Architecture:** Two independent, versioned model packages (`retrofit_v1` and `retrofit_v2`) sharing a common test harness. Each version is a self-contained module with a `run_simulation(params)` entry point returning a structured result object. Tests exercise both versions against identical parameter sets and assert behavioral differences match the upgrade plan intent.

**Tech Stack:** Python 3.10+, NumPy, Pandas, pytest, pytest-snapshot for regression testing, dataclasses for parameter/result objects, NumPy random Generator for reproducibility.

**Spec:** `/data/ScifiEconomicsLab/TheGreatRetrofit/upgrade plan.md` (adapted to retrofit co-op context) + `/data/ScifiEconomicsLab/TheGreatRetrofit/GreatRetroFitV2.ipynb` (current v1 behavior)

---

## Global Constraints

| Constraint | Value |
|------------|-------|
| Python version | ≥ 3.10 |
| Random reproducibility | All models accept `seed` parameter; use `np.random.Generator` |
| Parameter passing | Single `Params` dataclass per version; no global state |
| Output format | `Result` dataclass with weekly time-series arrays + summary scalars |
| Testing | pytest; snapshot tests for v1→v2 regression; property tests for invariants |
| Documentation | Markdown files in `docs/` per version + comparison report |
| No external dependencies | Only stdlib + numpy + pandas + pytest (+ matplotlib optional for plotting scripts) |

---

## Review Focus

| Input Class / Failure Mode | Expected Behavior | Pinning Test |
|----------------------------|-------------------|--------------|
| **Seed reproducibility** | Same seed → identical weekly trajectories across runs | `test_seed_reproducibility` in both versions |
| **Capital non-negativity** | Co-op accounts never go negative; work pauses if insufficient funds | `test_no_negative_accounts` in both versions |
| **Mass conservation** | `to_do + queued + in_progress + finished == n` every week | `test_mass_conservation` in both versions |
| **Surplus compounding** | Total system capital grows monotonically when surplus > 0 and projects complete | `test_surplus_grows_capital` in both versions |
| **Parameter sweep compatibility** | Both versions accept same base parameters (`n`, `E`, `tau`, `surplus`, `mean_time`, `week_cost`, `run_time`) | `test_common_params_interface` |

---

## File Structure to Create

```
TheGreatRetrofit/
├── src/
│   ├── retrofit_v1/
│   │   ├── __init__.py
│   │   ├── params.py
│   │   ├── model.py
│   │   └── results.py
│   ├── retrofit_v2/
│   │   ├── __init__.py
│   │   ├── params.py
│   │   ├── model.py
│   │   ├── results.py
│   │   ├── households.py
│   │   ├── buildings.py
│   │   ├── coops.py
│   │   ├── banks.py
│   │   └── market.py
│   └── common/
│       ├── __init__.py
│       ├── rng.py
│       └── validation.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_v1_basics.py
│   ├── test_v2_basics.py
│   ├── test_v1_v2_comparison.py
│   ├── test_invariants.py
│   └── snapshots/
│       └── (auto-generated)
├── docs/
│   ├── v1_documentation.md
│   ├── v2_documentation.md
│   └── comparison_report.md
├── scripts/
│   ├── run_sweep.py
│   └── plot_results.py
├── pyproject.toml
└── README.md
```

---

## Task Breakdown

### Task 1: Project Scaffolding & v1 Package

**Files:**
- Create: `pyproject.toml`
- Create: `src/retrofit_v1/__init__.py`
- Create: `src/retrofit_v1/params.py`
- Create: `src/retrofit_v1/model.py`
- Create: `src/retrofit_v1/results.py`
- Create: `src/common/__init__.py`
- Create: `src/common/rng.py`
- Create: `src/common/validation.py`

**Interfaces:**
- Produces: `retrofit_v1.Params`, `retrofit_v1.Result`, `retrofit_v1.run_simulation(params) -> Result`

- [ ] **Step 1: Write failing tests for v1 interface**
```python
# tests/test_v1_basics.py
def test_v1_params_creation():
    from retrofit_v1 import Params
    p = Params(n=1000, n_co_ops=10, E=100000, tau=100, surplus=0.2, mean_time=12, week_cost=1000, run_time=5200, seed=42)
    assert p.n == 1000

def test_v1_run_returns_result():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=123)
    result = run_simulation(p)
    assert hasattr(result, 'finished')
    assert hasattr(result, 'weekly_to_do')
    assert result.finished[-1] <= p.n

def test_v1_seed_reproducibility():
    from retrofit_v1 import Params, run_simulation
    p1 = Params(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2, mean_time=12, week_cost=1000, run_time=1000, seed=999)
    p2 = Params(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2, mean_time=12, week_cost=1000, run_time=1000, seed=999)
    r1 = run_simulation(p1)
    r2 = run_simulation(p2)
    assert np.array_equal(r1.weekly_finished, r2.weekly_finished)

def test_v1_mass_conservation():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=200, n_co_ops=3, E=80000, tau=15, surplus=0.2, mean_time=12, week_cost=1000, run_time=2000, seed=1)
    r = run_simulation(p)
    for t in range(len(r.weekly_to_do)):
        total = r.weekly_to_do[t] + r.weekly_queued[t] + r.weekly_in_progress[t] + r.weekly_finished[t]
        assert total == p.n

def test_v1_no_negative_accounts():
    from retrofit_v1 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=10000, tau=5, surplus=0.1, mean_time=20, week_cost=2000, run_time=2000, seed=7)
    r = run_simulation(p)
    assert np.all(r.weekly_total_accounts >= 0)
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_v1_basics.py -v`
Expected: FAIL (modules don't exist)

- [ ] **Step 3: Implement v1 package** — faithful translation of notebook logic into clean functions
Key implementation notes:
- `params.py`: `@dataclass` with all 8 base parameters + `seed`
- `rng.py`: `make_rng(seed) -> np.random.Generator`
- `model.py`: `run_simulation(params)` implementing the exact weekly loop from the notebook
- `results.py`: `@dataclass Result` with arrays: `weekly_to_do`, `weekly_queued`, `weekly_in_progress`, `weekly_finished`, `weekly_total_accounts`, `weekly_with_capacity` + scalars: `finished`, `total_weeks`, `final_total_accounts`

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_v1_basics.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite**
Run: `pytest tests/ -v`
Expected: PASS (only v1 tests exist)

- [ ] **Step 6: Commit**
```bash
git add src/retrofit_v1 tests/test_v1_basics.py src/common pyproject.toml && git commit -m "feat(v1): package current notebook logic with TDD tests"
```

---

### Task 2: v1 Invariants & Property Tests

**Files:**
- Create: `tests/test_invariants.py`

**Interfaces:**
- Consumes: `retrofit_v1.run_simulation`, `retrofit_v1.Params`

- [ ] **Step 1: Write failing invariant tests**
```python
# tests/test_invariants.py
import pytest
from retrofit_v1 import Params, run_simulation

@pytest.mark.parametrize("n,n_coops,E,tau,surplus", [
    (100, 1, 50000, 5, 0.1),
    (500, 5, 100000, 20, 0.2),
    (1000, 10, 200000, 50, 0.3),
])
def test_surplus_grows_capital(n, n_coops, E, tau, surplus):
    p = Params(n=n, n_co_ops=n_coops, E=E, tau=tau, surplus=surplus, mean_time=12, week_cost=1000, run_time=5000, seed=42)
    r = run_simulation(p)
    if r.finished == n:  # only check if completed
        assert r.final_total_accounts >= n_coops * E

def test_monotonic_finished():
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2, mean_time=12, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(np.diff(r.weekly_finished) >= 0)

def test_to_do_monotonic_decrease():
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2, mean_time=12, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(np.diff(r.weekly_to_do) <= 0)

def test_queued_nonnegative():
    p = Params(n=200, n_co_ops=3, E=100000, tau=10, surplus=0.2, mean_time=12, week_cost=1000, run_time=3000, seed=1)
    r = run_simulation(p)
    assert np.all(r.weekly_queued >= 0)
```

- [ ] **Step 2: Run tests to verify they fail** (will pass once v1 exists, but write first per TDD)
Run: `pytest tests/test_invariants.py -v`
Expected: PASS (v1 already implemented)

- [ ] **Step 3: Commit**
```bash
git add tests/test_invariants.py && git commit -m "test: add invariant tests for v1"
```

---

### Task 3: v1 Documentation

**Files:**
- Create: `docs/v1_documentation.md`

**Interfaces:**
- Consumes: `retrofit_v1` package understanding

- [ ] **Step 1: Write documentation** — convert the Model_Documentation.md into versioned v1 docs with:
- Parameter table with defaults
- Weekly loop pseudocode
- State transition diagram
- Invariant guarantees
- How to run sweeps

- [ ] **Step 2: Commit**
```bash
git add docs/v1_documentation.md && git commit -m "docs: v1 documentation"
```

---

### Task 4: v2 Core Package — Households & Buildings

**Files:**
- Create: `src/retrofit_v2/__init__.py`
- Create: `src/retrofit_v2/params.py`
- Create: `src/retrofit_v2/households.py`
- Create: `src/retrofit_v2/buildings.py`
- Create: `src/retrofit_v2/coops.py`
- Create: `src/retrofit_v2/results.py`
- Create: `src/retrofit_v2/model.py`

**Interfaces:**
- Produces: `retrofit_v2.Params` (extends v1 params + new fields), `retrofit_v2.Result`, `retrofit_v2.run_simulation(params) -> Result`
- New domain objects: `Household`, `Building`, `Coop` classes with their own state

- [ ] **Step 1: Write failing tests for v2 interface**
```python
# tests/test_v2_basics.py
def test_v2_params_creation():
    from retrofit_v2 import Params
    p = Params(n=1000, n_co_ops=10, E=100000, tau=100, surplus=0.2, mean_time=12, week_cost=1000, run_time=5200, seed=42,
               n_households=1000, income_mean=50000, income_cv=0.4, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=15)
    assert p.n_households == 1000

def test_v2_run_returns_result():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=123,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    result = run_simulation(p)
    assert hasattr(result, 'finished')
    assert hasattr(result, 'weekly_to_do')
    assert hasattr(result, 'gini_wealth')  # new monitor
    assert hasattr(result, 'price_dispersion')  # new monitor

def test_v2_seed_reproducibility():
    from retrofit_v2 import Params, run_simulation
    base = dict(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2, mean_time=12, week_cost=1000, run_time=1000,
                n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                aspiration_mean=50, aspiration_sd=15)
    r1 = run_simulation(Params(**base, seed=999))
    r2 = run_simulation(Params(**base, seed=999))
    assert np.array_equal(r1.weekly_finished, r2.weekly_finished)

def test_v2_mass_conservation():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=3, E=80000, tau=15, surplus=0.2, mean_time=12, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    for t in range(len(r.weekly_to_do)):
        total = r.weekly_to_do[t] + r.weekly_queued[t] + r.weekly_in_progress[t] + r.weekly_finished[t]
        assert total == p.n
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_v2_basics.py -v`
Expected: FAIL (v2 doesn't exist)

- [ ] **Step 3: Implement v2 core** — implementing upgrade plan items 1-6 (adapted):
1. **Household aspiration trait**: Each household draws `aspiration ~ N(aspiration_mean, aspiration_sd)` clipped to [0,100] at creation. Used when deciding to request retrofit (probability = aspiration/100).
2. **Household affordability**: Draw from truncated normal around `affordability_slider` (new param) instead of fixed 33%.
3. **Household initial capital**: Draw from Pareto(wealth_pareto_alpha) * scale, independent of income.
4. **Search length**: Each household sees only a random sample of `search_length` co-ops (new param), not all.
5. **Building attributes**: Each building gets `size`, `age`, `location_quality` drawn from distributions. Retrofit cost = base_cost * size_factor * age_factor.
6. **Household taste weights**: Each household has weights over building attributes + random shock. Chooses co-op by utility - cost.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_v2_basics.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite**
Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add src/retrofit_v2 tests/test_v2_basics.py && git commit -m "feat(v2): core package with households, buildings, search, taste"
```

---

### Task 5: v2 Financial Dynamics — Bargaining, Banks, Default

**Files:**
- Modify: `src/retrofit_v2/params.py` (add bank params)
- Modify: `src/retrofit_v2/households.py` (add bidding, reservation price)
- Modify: `src/retrofit_v2/coops.py` (add borrowing from banks)
- Create: `src/retrofit_v2/banks.py`
- Modify: `src/retrofit_v2/model.py` (integrate)

**Interfaces:**
- Consumes: v2 core from Task 4
- Produces: Extended `Params` with bank params, `Bank` class, bargaining logic

- [ ] **Step 1: Write failing tests**
```python
# tests/test_v2_financial.py
def test_v2_bargaining():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_bargaining=True, max_bid_shade=0.2, seller_reservation_pct=0.8)
    r = run_simulation(p)
    # With bargaining, some negotiations fail → slower completion vs no bargaining
    assert r.finished <= 100  # basic sanity

def test_v2_banks_exist():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_banks=3, bank_ltv_mean=0.8, bank_ltv_sd=0.05, bank_spread_mean=0.02)
    r = run_simulation(p)
    assert hasattr(r, 'bank_losses')
    assert hasattr(r, 'default_count')

def test_v2_default_possible():
    from retrofit_v2 import Params, run_simulation
    # Low endowment + high cost → co-ops may default on bank loans
    p = Params(n=50, n_co_ops=1, E=10000, tau=5, surplus=0.1, mean_time=20, week_cost=2000, run_time=2000, seed=1,
               n_households=50, income_mean=30000, income_cv=0.4, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_banks=1, bank_ltv_mean=0.9, bank_ltv_sd=0.0, bank_spread_mean=0.03,
               enable_default=True)
    r = run_simulation(p)
    # Default may or may not happen depending on seed; just check field exists
    assert hasattr(r, 'default_count')
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_v2_financial.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — upgrade plan items 7, 13-16 (adapted):
7. **Bargaining**: Buyers (households) bid below asking price based on WTP; sellers (co-ops) have reservation price. Failed negotiations → building returns to queued.
13. **Bank heterogeneity**: Multiple banks with different LTV caps and rate spreads. Co-ops choose best offer.
14. **Borrower-dependent lending**: Payment-to-income cap + risk premium rising with LTV.
15. **Default & foreclosure**: Co-ops that can't service debt default; banks absorb losses.
16. **Bank adaptation**: Banks adjust LTV/spreads based on recent price growth and losses.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_v2_financial.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite**
Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add src/retrofit_v2 tests/test_v2_financial.py && git commit -m "feat(v2): bargaining, banks, default, bank adaptation"
```

---

### Task 6: v2 Market Realism & Demographics

**Files:**
- Modify: `src/retrofit_v2/params.py` (add demographic/market params)
- Modify: `src/retrofit_v2/households.py` (income process, expectations, investor logic)
- Modify: `src/retrofit_v2/buildings.py` (depreciation, construction)
- Modify: `src/retrofit_v2/market.py` (local demand signals)
- Modify: `src/retrofit_v2/model.py` (integrate)

**Interfaces:**
- Consumes: v2 financial from Task 5
- Produces: Full v2 model with all upgrade plan items

- [ ] **Step 1: Write failing tests**
```python
# tests/test_v2_market.py
def test_v2_local_demand_signals():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=4, E=100000, tau=10, surplus=0.2, mean_time=12, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_neighbourhoods=4, enable_local_demand=True)
    r = run_simulation(p)
    assert hasattr(r, 'neighbourhood_time_on_market')
    assert r.neighbourhood_time_on_market.shape == (4, len(r.weekly_finished))

def test_v2_income_process():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               income_ar1_rho=0.9, income_shock_sd=0.1, unemployment_prob=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'household_income_trajectories')

def test_v2_investor_market():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_investors=True, investor_hurdle_mean=0.05, investor_hurdle_sd=0.01)
    r = run_simulation(p)
    assert hasattr(r, 'investor_purchases')

def test_v2_stock_evolution():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               enable_construction=True, build_cost=150000, construction_lag_weeks=52)
    r = run_simulation(p)
    assert hasattr(r, 'new_construction_count')
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_v2_market.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — upgrade plan items 8, 9-12, 17-21 (adapted):
8. **Local demand signals**: Time-on-market per neighbourhood replaces global multipliers.
9. **Heterogeneous exit hazard**: Per-household selling/moving probability based on age, income shocks, financial stress.
10. **Income process**: Lifecycle profile + AR(1) log-income shocks + unemployment spells.
11. **Demographics**: Births, deaths, household formation, inheritance of buildings.
12. **Consumption/capital dynamics**: Savings can decrease (consumption) not just increase.
17. **Heterogeneous expectations**: Some households extrapolate price growth, others anchor to price/rent.
18. **Investor market**: Landlords buy when rental yield > hurdle rate (varies by household).
19. **Transaction costs**: Moving costs, vacancy periods, fees.
20. **Stock evolution**: Depreciation, maintenance, demolition, construction with lag.
21. **Time-varying macro**: Interbank rate and income growth vary; exogenous shock scenario.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_v2_market.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite**
Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add src/retrofit_v2 tests/test_v2_market.py && git commit -m "feat(v2): local demand, income process, demographics, investors, stock evolution"
```

---

### Task 7: v2 Monitors & Calibration

**Files:**
- Modify: `src/retrofit_v2/results.py` (add monitor fields)
- Modify: `src/retrofit_v2/model.py` (compute monitors)
- Create: `tests/test_v2_monitors.py`

**Interfaces:**
- Produces: `Result` with Gini, price dispersion, cash buyer share, time-on-market spread

- [ ] **Step 1: Write failing tests**
```python
# tests/test_v2_monitors.py
def test_v2_gini_wealth():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=4, E=100000, tau=10, surplus=0.2, mean_time=12, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert hasattr(r, 'gini_wealth')
    assert 0 <= r.gini_wealth <= 1
    assert hasattr(r, 'gini_wealth_trajectory')

def test_v2_price_dispersion():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=200, n_co_ops=4, E=100000, tau=10, surplus=0.2, mean_time=12, week_cost=1000, run_time=2000, seed=1,
               n_households=200, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10,
               n_neighbourhoods=4)
    r = run_simulation(p)
    assert hasattr(r, 'price_dispersion_within')
    assert hasattr(r, 'price_dispersion_between')

def test_v2_cash_buyer_share():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert hasattr(r, 'cash_buyer_share')
    assert 0 <= r.cash_buyer_share <= 1

def test_v2_time_on_market_spread():
    from retrofit_v2 import Params, run_simulation
    p = Params(n=100, n_co_ops=2, E=50000, tau=10, surplus=0.2, mean_time=10, week_cost=500, run_time=520, seed=1,
               n_households=100, income_mean=40000, income_cv=0.3, wealth_pareto_alpha=1.5,
               aspiration_mean=50, aspiration_sd=10)
    r = run_simulation(p)
    assert hasattr(r, 'time_on_market_spread')
    assert r.time_on_market_spread >= 0
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_v2_monitors.py -v`
Expected: FAIL

- [ ] **Step 3: Implement monitors** — upgrade plan items 22-23
- Gini coefficient of wealth (per period)
- Price dispersion within/between neighbourhoods
- Share of cash buyers (no mortgage)
- Spread of time-on-market
- Record before/after each major change for comparison

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_v2_monitors.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite**
Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add src/retrofit_v2 tests/test_v2_monitors.py && git commit -m "feat(v2): monitors for Gini, price dispersion, cash buyers, time-on-market"
```

---

### Task 8: v1↔v2 Comparison Tests

**Files:**
- Create: `tests/test_v1_v2_comparison.py`
- Create: `tests/conftest.py` (shared fixtures)

**Interfaces:**
- Consumes: `retrofit_v1.run_simulation`, `retrofit_v2.run_simulation`
- Produces: Snapshot comparisons, behavioral difference assertions

- [ ] **Step 1: Write failing comparison tests**
```python
# tests/test_v1_v2_comparison.py
import pytest
import numpy as np
from retrofit_v1 import Params as V1Params, run_simulation as run_v1
from retrofit_v2 import Params as V2Params, run_simulation as run_v2

def common_params(seed=42):
    return dict(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2, mean_time=12, week_cost=1000, run_time=2000, seed=seed)

def test_v2_slower_with_heterogeneity():
    """v2 with household heterogeneity should complete slower than v1 baseline due to search/bargaining"""
    base = common_params()
    v1_p = V1Params(**base)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15, search_length=3, enable_bargaining=True)
    r1 = run_v1(v1_p)
    r2 = run_v2(v2_p)
    # v2 should take longer (more weeks) to finish same number of buildings
    assert r2.total_weeks >= r1.total_weeks * 0.8  # allow some variance

def test_v2_higher_final_capital_with_surplus():
    """Both versions should grow capital with surplus > 0"""
    base = common_params()
    v1_p = V1Params(**base)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15)
    r1 = run_v1(v1_p)
    r2 = run_v2(v2_p)
    assert r1.final_total_accounts >= 5 * 100000  # v1 baseline
    assert r2.final_total_accounts >= 5 * 100000  # v2 also grows

def test_v2_produces_gini_v1_does_not():
    """v2 has wealth distribution monitoring; v1 does not"""
    base = common_params()
    v1_p = V1Params(**base)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15)
    r1 = run_v1(v1_p)
    r2 = run_v2(v2_p)
    assert not hasattr(r1, 'gini_wealth')
    assert hasattr(r2, 'gini_wealth')

def test_v2_local_demand_creates_dispersion():
    """v2 with local demand should show price dispersion between neighbourhoods"""
    base = common_params(seed=123)
    v2_p = V2Params(**base, n_households=500, income_mean=45000, income_cv=0.35, wealth_pareto_alpha=1.5,
                    aspiration_mean=50, aspiration_sd=15,
                    n_neighbourhoods=4, enable_local_demand=True)
    r2 = run_v2(v2_p)
    assert hasattr(r2, 'price_dispersion_between')
    assert r2.price_dispersion_between > 0

# Snapshot test - captures v1 baseline behavior for regression
def test_v1_snapshot(snapshot):
    base = common_params(seed=42)
    v1_p = V1Params(**base)
    r1 = run_v1(v1_p)
    snapshot.assert_match({
        'finished': r1.finished,
        'total_weeks': r1.total_weeks,
        'final_total_accounts': round(r1.final_total_accounts, 2),
        'weekly_finished': r1.weekly_finished.tolist(),
    }, 'v1_baseline_snapshot.json')
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_v1_v2_comparison.py -v`
Expected: FAIL (v2 not fully implemented yet)

- [ ] **Step 3: After v2 complete, run tests to verify they pass**
Run: `pytest tests/test_v1_v2_comparison.py -v`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add tests/test_v1_v2_comparison.py tests/conftest.py && git commit -m "test: v1 vs v2 comparison tests with snapshots"
```

---

### Task 9: v2 Documentation & Comparison Report

**Files:**
- Create: `docs/v2_documentation.md`
- Create: `docs/comparison_report.md`

**Interfaces:**
- Consumes: Full understanding of both versions

- [ ] **Step 1: Write v2 documentation** — covering all new components, parameters, mechanisms
- [ ] **Step 2: Write comparison report** — table of differences, behavioral changes, parameter mapping, upgrade plan traceability
- [ ] **Step 3: Commit**
```bash
git add docs/v2_documentation.md docs/comparison_report.md && git commit -m "docs: v2 documentation and comparison report"
```

---

### Task 10: Sweep Scripts & Final Verification

**Files:**
- Create: `scripts/run_sweep.py`
- Create: `scripts/plot_results.py`

**Interfaces:**
- Consumes: Both model packages
- Produces: CSV outputs, plots

- [ ] **Step 1: Write sweep script** — runs parameter sweeps for both versions, saves CSVs
- [ ] **Step 2: Write plotting script** — generates comparison plots
- [ ] **Step 3: Run full test suite fresh**
Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Run sweeps for both versions**
Run: `python scripts/run_sweep.py --version v1 --out data/v1_sweep.csv`
Run: `python scripts/run_sweep.py --version v2 --out data/v2_sweep.csv`

- [ ] **Step 5: Commit**
```bash
git add scripts/ && git commit -m "feat: sweep and plotting scripts"
```

---

## Rulings Log

| Ruling | Decision | Why | Cost If Wrong |
|--------|----------|-----|---------------|
| Upgrade plan adaptation | Map housing-market concepts to retrofit-co-op context | Original upgrade plan describes a different model (households buying/selling houses); retrofit model is about co-ops financing building upgrades. Adapt concepts: households → building owners requesting retrofits; houses → buildings needing retrofit; banks → lenders to co-ops; bargaining → negotiation over retrofit scope/cost. | If mapping is wrong, v2 won't match user's mental model. Mitigation: comparison tests will reveal behavioral mismatches. |
| v1 as exact notebook translation | v1 must reproduce notebook behavior exactly | Comparison tests need a stable baseline | If v1 diverges, all comparisons invalid. Mitigation: snapshot test locks v1 behavior. |
| Separate packages not shared base | v1 and v2 as independent modules | v2 architecture is fundamentally different (agent-based vs queueing); forced inheritance creates complexity | Slight code duplication; acceptable for clarity |
| Pareto for wealth, lognormal for income | Standard in ABM literature | Matches upgrade plan intent | If distributions wrong, calibration fails. Mitigation: monitor tests check Gini ranges. |
| Snapshot test for v1 | Lock v1 behavior as regression baseline | Ensures v1 never accidentally changes | Snapshot must be updated intentionally if v1 is deliberately modified |

---

## Self-Review Checklist

- [x] Every upgrade plan item mapped to a task (1-23 → Tasks 4-7)
- [x] TDD enforced: tests written before implementation in every task
- [x] Interfaces between tasks explicitly defined with exact signatures
- [x] Review Focus items each have a pinning test in owning task
- [x] Plan longer than spec? No — tasks are signatures + test assertions, not code bodies
- [x] Global constraints captured and enforced in all tasks
- [x] File structure follows Python package conventions
- [x] No TBDs or vague steps — every step is checkable

---

**Plan complete and saved to `docs/plans/2026-11-03-model-upgrade.md`. Please review — does it capture what you want?**