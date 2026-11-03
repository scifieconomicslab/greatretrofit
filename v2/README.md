# v2: Agent-Based Retrofit Co-op Model

## Overview

The **v2 model** extends v1 into a full **agent-based simulation** with heterogeneous households, buildings, financial markets, and spatial structure. It implements all 23 items from the upgrade plan, adapted from a housing market context to the retrofit co-op context.

## New Agents

### Household (Building Owner)
- **Income**: Lognormal with configurable mean/CV
- **Wealth**: Pareto(α), independent of income
- **Aspiration**: Truncated normal (0-100), request probability/week
- **Affordability**: Max income fraction for payments
- **Taste weights**: Dirichlet over [size, -age, location]
- **Age**: 25-75, affects mortality
- **Investor status**: 15% are landlords with hurdle rate
- **Expectations**: Extrapolator (50%) or fundamentalist
- **Employment**: AR(1) income process with unemployment shocks

### Building
- **Attributes**: size, age, location quality, neighbourhood
- **Retrofit time/cost**: Scaled by size and age
- **Condition**: 0-1, depreciates over time
- **States**: to_do → queued → in_progress → finished

### Co-op (Extended)
- **Loan portfolio**: Active loans from banks
- **Payment-to-income cap**: 30% of revenue
- **Loan requests**: Seeks best bank offer

### Bank
- **Heterogeneous LTV caps & rate spreads**
- **Risk-based pricing**: LTV premium, wealth cushion discount
- **Default processing**: 50% recovery on collateral
- **Adaptive terms**: Tighten after losses, loosen after price growth

## Key Mechanisms

1. **Limited Search** — Households see `search_length` random co-ops
2. **Bargaining** — Buyers bid below asking; sellers have reservation price
3. **Bank Lending** — Co-ops borrow for ~50% of projects; PTI cap at 30%
4. **Default & Foreclosure** — Banks check solvency, absorb losses
5. **Local Demand** — Time-on-market tracked per neighbourhood
6. **Income Process** — AR(1) log-income + unemployment spells
7. **Investor Market** — Landlords buy when yield + growth > hurdle
8. **Demographics** — Births/deaths, inheritance of buildings
9. **Depreciation** — Buildings degrade; retrofitted degrade slower
10. **Construction** — New buildings when price > 1.2× build cost

## Installation

```bash
pip install -e .[dev]
```

## Running the Model

```python
from retrofit_v2 import Params, run_simulation

params = Params(
    # Base parameters (same as v1)
    n=10000, n_co_ops=50, E=100000, tau=50, surplus=0.2,
    mean_time=12, time_var=4, week_cost=1000, run_time=5200, seed=42,
    
    # Household parameters
    n_households=10000, income_mean=45000, income_cv=0.35,
    wealth_pareto_alpha=1.5, aspiration_mean=50, aspiration_sd=15,
    
    # Search & matching
    search_length=5, n_neighbourhoods=10,
    
    # Bargaining
    enable_bargaining=True, max_bid_shade=0.2, seller_reservation_pct=0.8,
    
    # Banking
    n_banks=5, bank_ltv_mean=0.8, bank_ltv_sd=0.05,
    bank_spread_mean=0.02, enable_default=True,
    
    # Income process
    income_ar1_rho=0.95, income_shock_sd=0.1, unemployment_prob=0.001,
    
    # Investors & construction & demographics
    enable_investors=True, enable_construction=True, enable_demographics=True,
)
result = run_simulation(params)

print(f"Finished: {result.finished}/{params.n}")
print(f"Gini wealth: {result.gini_wealth:.3f}")
print(f"Price dispersion between NH: {result.price_dispersion_between:.3f}")
print(f"Defaults: {result.default_count}")
print(f"Investor purchases: {result.investor_purchases}")
```

## Monitors (Result Fields)

| Monitor | Description |
|---------|-------------|
| `gini_wealth`, `gini_wealth_trajectory` | Wealth inequality |
| `price_dispersion`, `_within`, `_between` | Market segmentation |
| `cash_buyer_share` | Financial access |
| `time_on_market_spread`, `neighbourhood_time_on_market` | Liquidity variation |
| `bank_losses`, `default_count`, `total_loan_volume` | Financial stability |
| `investor_purchases`, `new_construction_count` | Market activity |
| `population_trajectory`, `household_income_trajectories` | Demographics |

## Tests

```bash
# Run v2 tests
pytest v2/test_v2/ -v

# Run specific test suites
pytest v2/test_v2/test_v2_financial.py -v
pytest v2/test_v2/test_v2_market.py -v
pytest v2/test_v2/test_v2_monitors.py -v
```

## Parameter Sweeps

```bash
# Quick sweep
python scripts/run_sweep.py --version v2 --quick --out data/v2_sweep.csv

# Full sweep
python scripts/run_sweep.py --version v2 --out data/v2_sweep.csv
```

## Comparison with v1

```python
# Both versions share base parameters
from retrofit_v1 import Params as V1Params, run_simulation as run_v1
from retrofit_v2 import Params as V2Params, run_simulation as run_v2

base = dict(n=500, n_co_ops=5, E=100000, tau=20, surplus=0.2,
            mean_time=12, time_var=4, week_cost=1000, run_time=2000, seed=42)

r1 = run_v1(V1Params(**base))
r2 = run_v2(V2Params(**base, n_households=500, income_mean=45000, ...))

# v2 has additional monitors
print(r2.gini_wealth, r2.price_dispersion_between)
```

See `docs/comparison_report.md` for full parameter mapping and behavioral differences.

## Documentation

See `docs/v2_documentation.md` for detailed documentation.