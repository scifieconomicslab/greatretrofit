# v2 Retrofit Co-op Model Documentation

## Overview

The **v2 model** extends the v1 queueing-financial model into a full **agent-based simulation** with heterogeneous households, buildings, financial markets, and spatial structure. It implements all 23 items from the upgrade plan, adapted from a housing market context to the retrofit co-op context.

**Key principle**: Each agent (household, building, co-op, bank) is an explicit object with its own state and behavior. The model simulates weekly time steps where agents interact through markets (retrofit requests, co-op assignment, bank lending, investor purchases).

---

## Agents

### Household (Building Owner)

Each household is an autonomous agent with persistent traits drawn once at creation:

| Attribute | Distribution | Role |
|-----------|--------------|------|
| **Income** | LogNormal(μ, σ) | Annual earnings; drives affordability |
| **Wealth** | Pareto(α) | Savings; independent of income |
| **Aspiration** | TruncatedNormal(μ, σ) ∈ [0, 100] | Weekly retrofit request probability = aspiration/100 |
| **Affordability** | TruncatedNormal(0.33, 0.1) ∈ [0.05, 0.6] | Max income fraction for payments |
| **Taste weights** | Dirichlet(2,2,2) | Preferences over [size, -age, location] |
| **Taste shock** | Normal(0, 0.5) | Idiosyncratic preference per building |
| **Age** | Uniform(25, 75) | Mortality risk, lifecycle effects |
| **Investor status** | Bernoulli(0.15) | 15% are landlords |
| **Hurdle rate** | Normal(0.05, 0.01) ∈ [0.02, 0.15] | Min return for investment |
| **Expectations** | Bernoulli(0.5) | Extrapolator vs fundamentalist |
| **Employment** | AR(1) + unemployment shocks | Income dynamics |

**Retrofit request**: Each week, if household owns a building in `to_do`, it requests retrofit with probability `aspiration / 100`.

**Bidding**: When matched with a co-op, household bids `asking_price × (1 - shade)` where `shade ∈ [0, max_bid_shade × affordability_pressure]`. Negotiation fails if bid < `asking_price × seller_reservation_pct`.

### Building

Each building has persistent physical attributes:

| Attribute | Distribution | Role |
|-----------|--------------|------|
| **Size** | LogNormal(0, 0.3) | Scales retrofit time and cost |
| **Age** | Uniform(0, 80) | Older = longer retrofit, worse condition |
| **Location quality** | Beta(2, 2) | Neighborhood amenity |
| **Neighbourhood** | Assigned | Spatial index for local markets |
| **Retrofit time** | Derived | `base_time × size × (1 + age/100)` weeks |
| **Retrofit cost** | Derived | `week_cost × time × size` euros |
| **Condition** | Derived | `1 - age/100 + noise` ∈ [0.2, 1.0] |
| **State** | Enum | `to_do` → `queued` → `in_progress` → `finished` |

**Key**: Cost scales with size and duration. A larger building takes longer *and* costs more per week.

### Co-op (Retrofit Cooperative)

Financial engines that execute retrofits:

| Attribute | Role |
|-----------|------|
| **Account** | Current cash balance (€) |
| **Projects** | Building IDs currently in progress |
| **Completed** | Finished building IDs |
| **Total revenue** | Cumulative income |
| **Loans** | Active bank loans with weekly payments |
| **Loan payments** | Weekly debt service |

**Capacity check**: Co-op can take a new project if:
1. `account ≥ sum(retrofit_cost of current projects) + new_project_cost`
2. Payment-to-income ratio < 30%: `annual_outflow / total_revenue < 0.3`

**Weekly cost**: Sum of `retrofit_cost / retrofit_time` for each active project (varies by building).

**Loan request**: For ~50% of projects, co-op seeks best bank offer (lowest rate).

### Bank

Heterogeneous lenders with adaptive behavior:

| Attribute | Distribution | Role |
|-----------|--------------|------|
| **LTV cap** | Normal(μ, σ) ∈ [0.5, 0.95] | Max loan-to-value |
| **Rate spread** | Normal(μ, σ) ∈ [0.005, 0.05] | Over base rate |
| **Capital** | Fixed 1,000,000 | Lending capacity |

**Loan pricing**: `rate = 3% + spread + risk_premium`
- Risk premium = 1% × (LTV / LTV_cap) × (1 - 0.5 × wealth_cushion)

**Default check**: Weekly; triggers if `coop.account < -0.1 × loan_remaining`
- Recovery: 50% of principal
- Bank absorbs loss, reduces capital

**Adaptation** (per step): `LTV_cap *= (1 - 0.1×losses + 0.05×price_growth)`, `spread *= (1 + 0.2×losses - 0.1×price_growth)`

---

## Core Mechanisms

### 1. Retrofit Request (Weekly)
Each household with a `to_do` building requests retrofit with probability `aspiration/100`. Buildings move `to_do → queued`.

### 2. Limited Search & Matching
Household sees `search_length` random co-ops (default: all). Among those with capacity, one is chosen randomly. Building moves `queued → in_progress`.

### 3. Bargaining
- Buyer bid: `asking_price × (1 - shade)`, `shade ∈ [0, max_bid_shade × affordability_pressure]`
- Seller reservation: `asking_price × seller_reservation_pct`
- Failed negotiation → building returns to `queued`

### 4. Bank Lending
- Co-op requests loan for ~50% of projects
- Banks offer terms based on LTV, spread, risk premium
- Co-op chooses lowest rate
- Payment-to-income cap: annual debt service < 30% of revenue

### 5. Construction Execution
- Weekly cost = `retrofit_cost / retrofit_time` per project
- Co-op pays weekly if `account ≥ weekly_cost`
- On completion: co-op receives `(1 + surplus) × negotiated_price`
- Household pays `negotiated_price` from wealth

### 6. Default & Foreclosure
- Banks check weekly: `coop.account < -0.1 × loan_remaining`
- On default: 50% recovery, bank absorbs loss, loan marked processed (no double-counting)

### 7. Local Demand Signals
- Time-on-market tracked per neighbourhood
- Replaces global demand multipliers; hot/cold areas emerge

### 8. Income Process
- AR(1) on log income: `log_y_t = ρ·log_y_{t-1} + (1-ρ)·log(μ) + ε`
- Unemployment: 30% income replacement, 10%/week job finding

### 9. Investor Market
- 15% of households are investors with hurdle rate
- Investors buy finished buildings when `rental_yield + expected_growth > hurdle_rate`
- Rent = 5% of building cost/year
- Buildings removed from `finished` after investor purchase (no re-sale)

### 10. Demographics
- Deaths: weekly prob = `death_rate/52` (×3 if age > 65)
- Dead household's building → `to_do`
- Births: Poisson(`len(households) × birth_rate/52`)

### 11. Building Depreciation
- Weekly: `condition -= depreciation_rate/52`
- Retrofitted buildings depreciate at half rate
- Value = `retrofit_cost × condition`

### 12. New Construction
- Triggered when avg finished price > 1.2 × `build_cost` in neighbourhood
- 10%/week chance per qualifying neighbourhood

---

## Parameters

### Base (from v1)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `n` | 100000 | Buildings needing retrofit |
| `n_co_ops` | 100 | Number of cooperatives |
| `E` | 100000 | Initial endowment per co-op (€) |
| `tau` | 100 | Mean weekly requests (Poisson) |
| `surplus` | 0.2 | Co-op surplus rate |
| `mean_time` | 12 | Mean retrofit weeks |
| `time_var` | 4 | Duration variance (±) |
| `week_cost` | 1000 | Weekly cost per project (€) |
| `run_time` | 5200 | Max weeks (100 years) |
| `seed` | None | Random seed |

### Household
| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_households` | 1000 | Number of households |
| `income_mean` | 50000 | Mean income (€/year) |
| `income_cv` | 0.4 | Income coefficient of variation |
| `wealth_pareto_alpha` | 1.5 | Pareto shape for wealth |
| `aspiration_mean` | 50 | Mean aspiration (0-100) |
| `aspiration_sd` | 15 | Aspiration std dev |

### Search/Matching
| Parameter | Default | Description |
|-----------|---------|-------------|
| `search_length` | 0 | Co-ops considered (0=all) |

### Spatial
| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_neighbourhoods` | 1 | Number of neighbourhoods |

### Bargaining
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_bargaining` | False | Enable bargaining |
| `max_bid_shade` | 0.2 | Max bid reduction fraction |
| `seller_reservation_pct` | 0.8 | Min acceptable fraction |

### Banking
| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_banks` | 0 | Number of banks |
| `bank_ltv_mean` | 0.8 | Mean LTV cap |
| `bank_ltv_sd` | 0.05 | LTV std dev |
| `bank_spread_mean` | 0.02 | Mean rate spread |
| `bank_spread_sd` | 0.005 | Spread std dev |
| `enable_default` | False | Enable default |

### Income Process
| Parameter | Default | Description |
|-----------|---------|-------------|
| `income_ar1_rho` | 0.0 | AR(1) persistence (0=off) |
| `income_shock_sd` | 0.0 | Shock std dev |
| `unemployment_prob` | 0.0 | Weekly unemployment prob |

### Investors
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_investors` | False | Enable investor market |
| `investor_hurdle_mean` | 0.05 | Mean hurdle rate |
| `investor_hurdle_sd` | 0.01 | Hurdle std dev |

### Stock Evolution
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_construction` | False | Enable new construction |
| `build_cost` | 150000 | Construction cost (€) |
| `construction_lag_weeks` | 52 | Lag (not yet used) |
| `depreciation_rate` | 0.01 | Annual depreciation |

### Demographics
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_demographics` | False | Enable births/deaths |
| `birth_rate` | 0.01 | Annual birth rate |
| `death_rate` | 0.01 | Annual death rate |

### Expectations
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_heterogeneous_expectations` | False | Enable expectation types |
| `extrapolator_share` | 0.5 | Fraction extrapolators |

### Transaction Costs
| Parameter | Default | Description |
|-----------|---------|-------------|
| `transaction_cost_pct` | 0.05 | Transaction cost fraction |
| `moving_cost` | 10000 | Moving cost (€) |

---

## Monitors (Result Fields)

### Base Weekly Time Series (from v1)
| Monitor | Description |
|---------|-------------|
| `weekly_to_do` | Buildings not yet requesting retrofit per week |
| `weekly_queued` | Buildings waiting for co-op assignment per week |
| `weekly_in_progress` | Buildings currently being retrofitted per week |
| `weekly_finished` | Cumulative completed buildings per week |
| `weekly_total_accounts` | Total capital across all co-ops per week |
| `weekly_with_capacity` | Number of co-ops with capacity per week |
| `finished` | **Total buildings completed** (including investor-purchased) |
| `total_weeks` | Number of weeks simulated |
| `final_total_accounts` | Total capital across all co-ops at end |

### Core V2 Weekly Time Series
| Monitor | Description |
|---------|-------------|
| `gini_wealth` | Final Gini of household wealth |
| `gini_wealth_trajectory` | Weekly Gini of household wealth |
| `weekly_income_gini` | Weekly Gini of household income (sample) |
| `price_dispersion` | Overall price CV (coefficient of variation) |
| `price_dispersion_within` | Avg within-neighbourhood price CV |
| `price_dispersion_between` | Between-neighbourhood CV of mean prices |
| `cash_buyer_share` | Fraction of retrofits paid without borrowing |
| `time_on_market_spread` | Max-min avg time-on-market across neighbourhoods |
| `neighbourhood_time_on_market` | Per-neighbourhood weekly time-on-market |
| `cash_buyer_share` | Fraction of retrofits paid without borrowing |
| `household_income_trajectories` | Sample household income paths per week |
| `investor_purchases` | Total investor acquisitions |
| `new_construction_count` | New buildings added |
| `population_trajectory` | Household count over time |
| `finished` | **Total buildings completed** (including investor-purchased) |

### Additional Weekly Time Series (New)
| Monitor | Description |
|---------|-------------|
| `weekly_failed_negotiations` | Failed bargaining attempts per week |
| `weekly_defaults` | Defaults occurring per week |
| `weekly_cumulative_defaults` | Cumulative defaults per week |
| `weekly_investor_purchases` | Investor acquisitions per week |
| `weekly_new_construction` | New buildings started per week |
| `weekly_avg_queue_wait` | Average weeks in queue per week |
| `weekly_max_queue_wait` | Maximum weeks in queue per week |
| `weekly_bank_losses` | Bank losses incurred per week |
| `weekly_cumulative_bank_losses` | Cumulative bank losses per week |
| `weekly_loan_volume` | Cumulative loan volume originated per week |
| `weekly_loan_payments` | Total loan payments made per week |
| `weekly_coop_revenue` | Cumulative co-op revenue per week |
| `weekly_unemployment_rate` | Fraction of households unemployed per week |
| `weekly_avg_retrofit_time` | Average retrofit duration of completions per week |
| `weekly_avg_retrofit_cost` | Average retrofit cost of completions per week |

### Per-Neighbourhood Weekly
| Monitor | Description |
|---------|-------------|
| `weekly_finished_per_nh` | Finished buildings per neighbourhood per week |
| `weekly_queue_per_nh` | Queued buildings per neighbourhood per week |
| `weekly_avg_price_per_nh` | Average retrofit price per neighbourhood per week |

### Financial Monitors
| Monitor | Description |
|---------|-------------|
| `bank_losses` | Total bank losses |
| `default_count` | Number of defaults (deduplicated) |
| `total_loan_volume` | Total originated |
| `cash_buyer_share` | Fraction of retrofits paid without borrowing |
| `time_on_market_spread` | Max-min avg time-on-market across neighbourhoods |

### Market Realism Monitors
| Monitor | Description |
|---------|-------------|
| `household_income_trajectories` | Sample income paths |
| `investor_purchases` | Total investor acquisitions |
| `new_construction_count` | New buildings added |
| `population_trajectory` | Household count over time |
| `finished` | **Total buildings completed** (including investor-purchased) |

### Additional Monitors
| Monitor | Description |
|---------|-------------|
| `weekly_failed_negotiations` | Failed bargaining attempts per week |
| `weekly_defaults` | Defaults occurring per week |
| `weekly_cumulative_defaults` | Cumulative defaults per week |
| `weekly_investor_purchases` | Investor purchases per week |
| `weekly_new_construction` | New buildings started per week |
| `weekly_avg_queue_wait` | Average weeks in queue per week |
| `weekly_max_queue_wait` | Maximum weeks in queue per week |
| `weekly_bank_losses` | Bank losses per week |
| `weekly_cumulative_bank_losses` | Cumulative bank losses per week |
| `weekly_loan_volume` | Loan volume per week |
| `weekly_loan_payments` | Loan payments per week |
| `weekly_coop_revenue` | Co-op revenue per week |
| `weekly_unemployment_rate` | Unemployment rate per week |
| `weekly_avg_retrofit_time` | Average retrofit duration of completions per week |
| `weekly_avg_retrofit_cost` | Average retrofit cost of completions per week |
| `weekly_finished_per_nh` | Finished per neighbourhood per week |
| `weekly_queue_per_nh` | Queue per neighbourhood per week |
| `weekly_avg_price_per_nh` | Average price per neighbourhood per week |

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

---

## Validation & Invariants

The model enforces several invariants (tested in `test_v2/test_v2/`):

| Invariant | Test |
|-----------|------|
| Mass conservation: `to_do + queued + in_progress + finished = n` | `test_mass_conservation` |
| Capital non-negative | `test_no_negative_accounts` |
| Gini ∈ [0, 1] | `test_gini_wealth_bounds` |
| Seed reproducibility | `test_seed_reproducibility` |
| Zero surplus → capital preserved | Manual validation |
| Default counting deduplicated | `test_default_possible` |

---

## Known Limitations

1. **Construction lag** parameter exists but not implemented as explicit delay
2. **Transaction costs** defined but not applied in bargaining/investor logic
3. **Moving costs** not used
4. **Heterogeneous expectations** only affect investor decisions, not retrofit timing
5. **Calibration** not yet done to Brussels microdata

---

## File Structure

```
v2/
├── src/retrofit_v2/
│   ├── __init__.py          # Package exports
│   ├── common/              # Embedded utilities (rng, validation)
│   ├── model.py             # Main simulation loop
│   ├── params.py            # Parameter dataclass + validation
│   ├── results.py           # Result dataclass
│   ├── households.py        # Household agent + creation
│   ├── buildings.py         # Building agent + creation + depreciation
│   ├── coops.py             # Co-op agent + loan logic
│   └── banks.py             # Bank agent + lending + default
├── test_v2/                 # 31 tests across 6 suites
├── docs/v2_documentation.md # This file
└── README.md                # Quick start
```