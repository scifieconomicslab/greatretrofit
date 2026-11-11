# v3: household retrofit decisions on the map of Jette

> **Every number in v3 is a placeholder.** The defaults exist so the structure runs and the tests mean something ([docs/placeholders.md](docs/placeholders.md)). Nothing computed from them is a finding: do not quote adoption by income, public cost, or any ranking of delivery modes from a default run.

v3 asks: **given who can pay, who gets the subsidy, and how the work is delivered, which households retrofit, and what does the state spend?** It was built to explore why tax rebates on retrofits may work poorly and be regressive. It is a new model, not an extension of v2. What changed from v1 and v2, and why: [docs/versions.md](../docs/versions.md).

## The model in one minute

Each month, each household in a dwelling on the map may *consider* retrofitting (a small monthly chance, higher in a condo where neighbours have done it or are canvassing). A household that considers retrofits if both hold:

- **it pays**: the NPV over the years it expects to stay is positive (bill savings plus any rebate, minus cash from savings and the discounted loan payments), and
- **it can be financed**: savings first, then a loan up to the household's credit limit.

What the household pays, and when, depends on the **delivery mode**:

| Mode | Household pays now | State pays | Catch |
|---|---|---|---|
| `rebate_market` | the full vendor price | a rebate, later, capped by the household's tax payable (unless refundable) | needs savings or credit, and tax to deduct against |
| `passthrough` | nothing | the full vendor price, at once | vendor margin |
| `public_service` | nothing | cost plus overhead, at once | limited capacity, rationed by a queue |

Condo owners decide for their own unit; the **shared parts** (windows, facade, roof) go to a floor-area-weighted vote that passes at a threshold (default two-thirds) only if every owner can pay their share. Rental buildings are a stub: shown grey, never modelled.

Full rules, equations, timing and the list of assumptions: [docs/model-spec.md](docs/model-spec.md).

## Three ways to run it

All three use the same rules and the same PRNG, so a seed means the same thing in each.

### 1. Python (reference implementation)

Stdlib only. From the repository root, after `pip install -e .[dev]` (or with `PYTHONPATH=v3/src`):

```python
from retrofit_v3 import Params, run_simulation

r = run_simulation(Params(seed=1))                    # 200 synthetic buildings, 180 months
print(r.n_buildings, r.n_units, r.adopted_units)
print(r.adoption_by_quintile)                         # structure check only, not a result

r = run_simulation(Params(seed=1, delivery_mode="public_service", means_test=True))
print(r.final_frame["series"]["public_cost"])
```

`run_simulation(params, on_step)` calls `on_step(frame)` at month 0 and after every month. `Result` holds the frames (if `keep_frames`), adoption events and vote events. The frame contract is [docs/frame-schema.md](docs/frame-schema.md).

### 2. In the browser, on the real map of Jette

`packs/great-retrofit/` is a [paperdolls](../packs/great-retrofit/README.md) model pack: a JavaScript port of the model (`runtime.js`), a scene binder (`bind.js`) and a manifest (`pack.yaml`) of sliders, presets, colours, charts and KPI tiles. The build turns it into one offline HTML page with the 8,105 residential buildings of Jette. Moving a slider re-runs 15 years in about a second.

```bash
scripts/build_jette_demo.sh                 # needs a paperdolls checkout (PAPERDOLLS_DIR)
ENRICHED=1 scripts/build_jette_demo.sh      # with real terrain and UrbIS building heights
```

Output: `build/jette_retrofit.html` (open with `file://`). What was checked in a real browser: [docs/verification/jette-integration.md](../docs/verification/jette-integration.md).

### 3. NetLogo

[`great-retrofit-v3.nlogox`](great-retrofit-v3.nlogox) is a single-file NetLogo 7 port: one patch per building (red: none done, orange: partly, green: all, grey: rental), sliders for every lever, plots of adoption by quintile, state spend, bills saved and cost per retrofit. Open it in NetLogo 7.0.4 or later, press **setup**, then **go**. Its Info tab explains the model and lists the known differences from Python (NetLogo's `round` rounds half away from zero; the 32-bit PRNG multiply is done in 16-bit limbs). Unlike the JavaScript port, the NetLogo port has no automated parity test.

## Levers

| Group | Parameters |
|---|---|
| Fiscal | `deduction_rate`, `refundable`, `rebate_lag_months`, `means_test`, `means_test_max_quintile` |
| Credit | `credit_access` (`income_tested` / `open` / `none`), `loan_rate`, `loan_rate_risk_premium`, `credit_income_threshold`, `credit_loan_to_income`, `loan_term_months` |
| Delivery | `delivery_mode`, `vendor_margin`, `public_overhead`, `public_capacity` |
| Energy | `energy_scenario` (`flat` / `rising` / `shock`) |
| Condo | `shared_measure`, `shared_share`, `vote_threshold`, `peer_effect`, `neighbour_boost`, canvassing hours |
| Tenure (placeholder rule) | `rental_share_single`, `rental_share_multi` |

The browser page has four presets: rebate only, pay the vendor direct, public retrofit service, and more rental buildings.

## Outputs

By income quintile: adoption, public transfer per euro of price, share able to pay the price now, household net cash over time, canvassing and leisure hours. Overall: cumulative public cost, bills saved, cost per retrofit split into base cost and margin or overhead, building state and tenure counts, shared-measure votes pending or approved. Per building: state, tenure, units, share retrofitted, mean income quintile, vote state. Definitions: [docs/model-spec.md §8](docs/model-spec.md#8-outputs).

## Code

```
v3/
├── src/retrofit_v3/
│   ├── params.py            # Params: every lever and placeholder, validated
│   ├── model.py             # the monthly loop (Simulation, run_simulation)
│   ├── npv.py               # discounted savings, rebate and loan payments
│   ├── financing.py         # savings first, then a loan within the credit limit
│   ├── rebate.py            # deduction, refundability, tax-capacity cap
│   ├── credit.py            # credit limit and loan rate by access rule
│   ├── ownership.py         # owner-occupied, condo, rental (stub)
│   ├── delivery.py          # rebate_market, passthrough, public_service quotes
│   ├── scene_entities.py    # map footprints -> buildings, units, tenure
│   ├── entities.py, frames.py, results.py
│   └── common/              # rng.py (mulberry32 + hash_uniform), validation.py
├── js/prng.js               # the same PRNG in JavaScript (copied into the pack)
├── great-retrofit-v3.nlogox # NetLogo port
├── test_v3/                 # invariants, mechanics, pure modules, PRNG vectors, docs sync
├── tools/gen_prng_vectors.py
└── docs/
```

All model randomness goes through the shared PRNG. Per-household, per-month draws use the stateless `hash_uniform(seed, household, month)`, so changing a policy lever never reshuffles other households' draws. Regenerate `test_v3/vectors/prng.json` with `tools/gen_prng_vectors.py` only if the PRNG definition changes, then copy `js/prng.js` into `packs/great-retrofit/`.

## Tests

```bash
pytest v3                          # model: invariants, mechanics, PRNG (also runs node v3/js/test_prng.js if node is installed)
pytest packs/great-retrofit/tests  # Python/JS parity on 24 golden trajectories, scene binding, manifest
pytest tests/model tests/fuzz      # regression tests for fixed defects, validation vectors, fuzzing
```

Some JavaScript tests need a paperdolls checkout next to this repository (or `PAPERDOLLS_DIR`); without it they fail or skip.

## Documentation

| Document | What it is |
|---|---|
| [docs/model-spec.md](docs/model-spec.md) | The specification: state, timing, decision rule, ownership, delivery, outputs, assumptions table, what the model can and cannot claim |
| [docs/placeholders.md](docs/placeholders.md) | Every placeholder value and the open question it waits on; the tenure rule |
| [docs/frame-schema.md](docs/frame-schema.md) | The per-month output contract between model and page |
| [docs/audit.md](docs/audit.md) | How much of the plan the first skeleton implemented, and what was added |
| [../docs/versions.md](../docs/versions.md) | What changed from v1 to v2 to v3 |
| [../docs/plans/2026-11-06-interactive-retrofit-plan.md](../docs/plans/2026-11-06-interactive-retrofit-plan.md) | The plan: v3, the paperdolls upgrade, the model pack |
| [../docs/calibration/](../docs/calibration/README.md) | Survey of public data for Jette and Brussels (not used by the model yet) |
| [../docs/state-machines.md](../docs/state-machines.md), [../docs/design-questions.md](../docs/design-questions.md) | State machines, defects found and fixed, three open design questions |
| [../packs/great-retrofit/README.md](../packs/great-retrofit/README.md) | The browser model pack |

## Not modelled

Landlords and split incentives, energy communities, moving and inheritance, phasing of works, vendor capacity and price response, collective loans or reserve funds for condos, the state's budget limit, and any social motive. Full list: [docs/model-spec.md §11](docs/model-spec.md#11-what-is-not-modelled-so-nobody-looks-for-it).
