# v2 Retrofit Co-op Model Documentation

## Overview

The v2 model extends the v1 queueing-financial model into a full **agent-based simulation** with heterogeneous households, buildings, financial markets, and spatial structure. It implements the upgrade plan items adapted to the retrofit co-op context.

---

## New Agents

### Household (Building Owner)
Each household has:
- **Income**: Lognormal(μ, σ) with configurable mean and CV
- **Wealth**: Pareto(α) independent of income
- **Aspiration**: Truncated normal (0-100), probability of requesting retrofit/week
- **Affordability**: Max fraction of income for retrofit payments (truncated normal ~33%)
- **Taste weights**: Dirichlet over [size, -age, location quality]
- **Age**: 25-75, affects mortality
- **Investor status**: 15% are landlords with hurdle rate
- **Expectations**: Extrapolator (50%) or fundamentalist
- **Employment**: AR(1) income process with unemployment shocks

### Building
Each building has:
- **Size**: Lognormal around 1.0
- **Age**: Uniform 0-80 years
- **Location quality**: Beta(2,2)
- **Neighbourhood**: Spatial index
- **Retrofit time/cost**: Scaled by size and age
- **Condition**: 0-1, depreciates over time
- **State**: to_do → queued → in_progress → finished

### Co-op
Extended with:
- **Loan portfolio**: Active loans from banks
- **Payment-to-income cap**: 30% of revenue
- **Loan requests**: Seeks best bank offer for projects

### Bank
- **LTV cap**: Heterogeneous, normal around mean
- **Rate spread**: Heterogeneous, normal around mean
- **Risk-based pricing**: LTV premium, wealth cushion discount
- **Default processing**: 50% recovery on collateral
- **Adaptive terms**: Tighten after losses, loosen after price growth

---

## Key Mechanisms

### 1. Household Retrofit Request
Each week, each household with a building in `to_do` requests retrofit with probability `aspiration/100`.

### 2. Limited Search & Matching
Households see only `search_length` random co-ops (default: all). Choose randomly among those with capacity.

### 3. Bargaining
- Buyer bids: `asking_price × (1 - shade)`, shade ∈ [0, max_bid_shade × affordability_pressure]
- Seller reservation: `asking_price × seller_reservation_pct`
- Failed negotiation → building returns to queued

### 4. Bank Lending
- Co-ops request loans for ~50% of projects
- Banks offer terms based on LTV cap, spread, risk premium
- Co-op chooses lowest rate
- Payment-to-income cap at 30%

### 5. Default & Foreclosure
- Banks check co-op solvency weekly
- Default if co-op account < -10% loan remaining
- 50% recovery, bank absorbs loss

### 6. Local Demand Signals
- Time-on-market tracked per neighbourhood
- Replaces global demand multipliers

### 7. Income Process
- AR(1) on log income: `log_y_t = ρ·log_y_{t-1} + (1-ρ)·log(μ) + ε`
- Unemployment spells: 30% income replacement, 10%/week job finding

### 8. Investor Market
- Landlords buy finished buildings when `rental_yield + expected_growth > hurdle_rate`
- Rent = 5% of building cost/year

### 9. Demographics
- Deaths: weekly prob = death_rate/52, ×3 if age>65
- Births: Poisson(len(households) × birth_rate/52)
- Dead household's building → to_do

### 10. Building Depreciation
- Weekly: `condition -= depreciation_rate/52`
- Retrofitted buildings depreciate at half rate

### 11. New Construction
- Triggered when avg finished price > 1.2 × build_cost in neighbourhood
- 10%/week chance, lag implicit in process

---

## Parameters

### Base (from v1)
| Parameter | Default | Description |
|-----------|---------|-------------|
| n | 100000 | Buildings needing retrofit |
| n_co_ops | 100 | Number of cooperatives |
| E | 100000 | Initial endowment per co-op (€) |
| tau | 100 | Mean weekly requests (Poisson) |
| surplus | 0.2 | Co-op surplus rate |
| mean_time | 12 | Mean retrofit weeks |
| time_var | 4 | Duration variance (±) |
| week_cost | 1000 | Weekly cost/project (€) |
| run_time | 5200 | Max weeks (100 years) |
| seed | None | Random seed |

### Household
| Parameter | Default | Description |
|-----------|---------|-------------|
| n_households | 1000 | Number of households |
| income_mean | 50000 | Mean income (€/year) |
| income_cv | 0.4 | Income coefficient of variation |
| wealth_pareto_alpha | 1.5 | Pareto shape for wealth |
| aspiration_mean | 50 | Mean aspiration (0-100) |
| aspiration_sd | 15 | Aspiration std dev |

### Search/Matching
| Parameter | Default | Description |
|-----------|---------|-------------|
| search_length | 0 | Co-ops considered (0=all) |

### Spatial
| Parameter | Default | Description |
|-----------|---------|-------------|
| n_neighbourhoods | 1 | Number of neighbourhoods |

### Bargaining
| Parameter | Default | Description |
|-----------|---------|-------------|
| enable_bargaining | False | Enable bargaining |
| max_bid_shade | 0.2 | Max bid reduction fraction |
| seller_reservation_pct | 0.8 | Min acceptable fraction |

### Banking
| Parameter | Default | Description |
|-----------|---------|-------------|
| n_banks | 0 | Number of banks |
| bank_ltv_mean | 0.8 | Mean LTV cap |
| bank_ltv_sd | 0.05 | LTV std dev |
| bank_spread_mean | 0.02 | Mean rate spread |
| bank_spread_sd | 0.005 | Spread std dev |
| enable_default | False | Enable default |

### Income Process
| Parameter | Default | Description |
|-----------|---------|-------------|
| income_ar1_rho | 0.0 | AR(1) persistence (0=off) |
| income_shock_sd | 0.0 | Shock std dev |
| unemployment_prob | 0.0 | Weekly unemployment prob |

### Investors
| Parameter | Default | Description |
|-----------|---------|-------------|
| enable_investors | False | Enable investor market |
| investor_hurdle_mean | 0.05 | Mean hurdle rate |
| investor_hurdle_sd | 0.01 | Hurdle std dev |

### Stock Evolution
| Parameter | Default | Description |
|-----------|---------|-------------|
| enable_construction | False | Enable new construction |
| build_cost | 150000 | Construction cost (€) |
| construction_lag_weeks | 52 | Lag (not yet used) |
| depreciation_rate | 0.01 | Annual depreciation |

### Demographics
| Parameter | Default | Description |
|-----------|---------|-------------|
| enable_demographics | False | Enable births/deaths |
| birth_rate | 0.01 | Annual birth rate |
| death_rate | 0.01 | Annual death rate |

### Expectations
| Parameter | Default | Description |
|-----------|---------|-------------|
| enable_heterogeneous_expectations | False | Enable expectation types |
| extrapolator_share | 0.5 | Fraction extrapolators |

### Transaction Costs
| Parameter | Default | Description |
|-----------|---------|-------------|
| transaction_cost_pct | 0.05 | Transaction cost fraction |
| moving_cost | 10000 | Moving cost (€) |

---

## Monitors (Result Fields)

| Monitor | Description |
|---------|-------------|
| gini_wealth | Final Gini of household wealth |
| gini_wealth_trajectory | Weekly Gini |
| price_dispersion | Overall price CV |
| price_dispersion_within | Avg within-neighbourhood CV |
| price_dispersion_between | Between-neighbourhood CV of means |
| cash_buyer_share | Fraction non-financed |
| time_on_market_spread | Max-min avg time-on-market |
| neighbourhood_time_on_market | Per-neighbourhood weekly time-on-market |
| bank_losses | Total bank losses |
| default_count | Number of defaults |
| total_loan_volume | Total originated |
| household_income_trajectories | Sample income paths |
| investor_purchases | Investor acquisitions |
| new_construction_count | New buildings added |
| population_trajectory | Household count over time |

---

## Running the Model

```python
from retrofit_v2 import Params, run_simulation

params = Params(
    n=10000,
    n_co_ops=50,
    E=100000,
    tau=50,
    surplus=0.2,
    mean_time=12,
    time_var=4,
    week_cost=1000,
    run_time=5200,
    seed=42,
    n_households=10000,
    income_mean=45000,
    income_cv=0.35,
    wealth_pareto_alpha=1.5,
    aspiration_mean=50,
    aspiration_sd=15,
    search_length=5,
    n_neighbourhoods=10,
    enable_bargaining=True,
    n_banks=5,
    enable_default=True,
    income_ar1_rho=0.95,
    income_shock_sd=0.1,
    unemployment_prob=0.001,
    enable_investors=True,
    enable_construction=True,
    enable_demographics=True,
)
result = run_simulation(params)

print(f"Finished: {result.finished}/{params.n}")
print(f"Gini wealth: {result.gini_wealth:.3f}")
print(f"Price dispersion between: {result.price_dispersion_between:.3f}")
print(f"Defaults: {result.default_count}")
```