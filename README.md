# The Great Retrofit

Simulation models of **housing energy retrofit in Brussels**. There are three versions, and they ask two different questions:

- **v1 and v2: the co-op question.** How do retrofit co-operatives, which have limited capital, work through a queue of buildings that need retrofitting, and how do owners, banks and neighbourhoods change that? Weekly steps.
- **v3: the policy question.** Given who can pay, who gets the subsidy and how the work is delivered, which households retrofit, and what does the state spend? In particular, why do tax rebates on retrofits work poorly, and why are they regressive? Monthly steps, run on the real building map of Jette, live in a browser.

Contributing models: **Nvidia Nemotron 3 Ultra** and **Beam 1.0**.

> **v3's numbers are all placeholders** awaiting the economists ([v3/docs/placeholders.md](v3/docs/placeholders.md)). Its runs show that the structure works, not what would happen in Jette. Do not quote results from them.

## The three versions

| | v1 | v2 | v3 |
|---|---|---|---|
| **What it is** | Faithful Python port of the original notebook (`Joffa's original/`) | v1 plus the 23 items of the upgrade plan: a full agent-based market | A new model for the rebate question; v2 stays as the co-op reference |
| **Paradigm** | Queueing and cash flow | Agent-based market | Agent-based household decision (NPV plus ability to finance) |
| **Agents** | Buildings, co-ops | Households, buildings, co-ops, banks, investors | Households in dwellings, buildings (owner-occupied, condo, rental stub), one lender, the state |
| **Who decides** | Nobody: Poisson requests | Owners request by aspiration; co-ops and banks respond | Each household, if the retrofit pays over its stay **and** it can finance it; condo owners vote on shared parts |
| **Money** | Co-op capital compounds with surplus | Bank loans, bargaining, default and foreclosure | Savings and credit; rebate capped by tax payable; three delivery modes |
| **Space** | None | Abstract neighbourhoods | Real footprints of Jette (8,105 residential buildings) |
| **Outputs** | Queue lengths, capital | Gini, price dispersion, time on market, bank losses | Adoption, public transfer, ability to pay and net cash **by income quintile**; public cost; cost per retrofit |
| **Runs in** | Python | Python, notebook | Python, JavaScript (browser), NetLogo |
| **Status** | Frozen | Frozen | Active |

**What each version added, what it dropped, and what each feature means: [docs/versions.md](docs/versions.md).**

## Quick start

```bash
pip install -e .[dev]
```

**v3**, the current model:

```python
from retrofit_v3 import Params, run_simulation

r = run_simulation(Params(seed=1, delivery_mode="rebate_market"))
print(r.n_buildings, r.n_units, r.adopted_units)
print(r.adoption_by_quintile)        # a structure check, not a finding
```

The browser page on the map of Jette (needs a [paperdolls](packs/great-retrofit/README.md) checkout; writes `build/jette_retrofit.html`):

```bash
scripts/build_jette_demo.sh
```

The NetLogo version: open `v3/great-retrofit-v3.nlogox` in NetLogo 7, press **setup**, then **go**.

More in [v3/README.md](v3/README.md).

**v1 and v2:**

```python
from retrofit_v1 import Params, run_simulation
r = run_simulation(Params(n=1000, n_co_ops=10, E=100000, tau=20, surplus=0.2, seed=42))
print(f"v1: {r.finished}/1000 buildings in {r.total_weeks} weeks")

from retrofit_v2 import Params, run_simulation
r = run_simulation(Params(n=1000, n_co_ops=10, E=100000, tau=20, surplus=0.2, seed=42,
                          n_households=1000, income_mean=45000, income_cv=0.35,
                          wealth_pareto_alpha=1.5, aspiration_mean=50, aspiration_sd=15,
                          search_length=5, n_neighbourhoods=10, enable_bargaining=True,
                          n_banks=5, enable_default=True, enable_investors=True,
                          enable_construction=True, enable_demographics=True))
print(f"v2: {r.finished}/1000 buildings, Gini={r.gini_wealth:.3f}")
```

v1 and v2 series are indexed by **week**; v3 frames by **month**. The v2 notebook `v2/TheGreatRetrofit_v2.ipynb` documents v2 and plots its series.

## Tests

```bash
pytest                                  # v1, v2, v3 (the default test paths)
pytest packs/great-retrofit/tests       # v3 browser runtime: Python/JS parity, scene binding, manifest
pytest tests/                           # v3 regression tests, validation vectors, fuzzing, geodata
```

The JavaScript tests need `node`; a few need a paperdolls checkout next to this repository (or `PAPERDOLLS_DIR`), and skip or fail without it. Geodata tests need `pip install -e .[geodata]`.

## Repository layout

```
TheGreatRetrofit/
├── v1/                     # Queueing-financial model (port of the original notebook)
├── v2/                     # Agent-based co-op market + notebook
├── v3/                     # Household retrofit-decision model
│   ├── src/retrofit_v3/    #   Python reference implementation
│   ├── js/prng.js          #   shared PRNG, JavaScript side
│   ├── great-retrofit-v3.nlogox  # NetLogo port
│   ├── test_v3/
│   └── docs/               #   spec, placeholders, frame schema, audit
├── packs/great-retrofit/   # paperdolls model pack: JS port of v3, scene binding, UI manifest, parity tests
├── tests/                  # v3 cross-language tests: regressions (model/), fuzzing (fuzz/), geodata/
├── scripts/                # v1/v2 sweeps and plots; Jette demo build; browser checks; geodata/ pipeline
├── docs/
│   ├── versions.md         #   v1 → v2 → v3: features and what they mean
│   ├── comparison_report.md  # v1 vs v2 in detail
│   ├── plans/              #   upgrade plan (v2), interactive retrofit plan (v3)
│   ├── calibration/        #   survey of public data for Jette and Brussels
│   ├── state-machines.md   #   v3 state machines, defects found and fixed
│   ├── design-questions.md #   three open modelling decisions
│   └── verification/       #   browser, phone and GPU checks of the Jette page
├── v1v2testcomparison/     # v1 vs v2 test results
├── Joffa's original/       # Original prototype notebook, its documentation and upgrade plan
├── data/                   # Sweep outputs (generated; *.csv and *.json are gitignored)
└── pyproject.toml
```

`cache/` and `build/` (scene downloads, the built page) are generated and gitignored.

## Documentation

| Document | Location |
|---|---|
| **Version history: v1 → v2 → v3** | [docs/versions.md](docs/versions.md) |
| v1 | [v1/README.md](v1/README.md), [v1/docs/v1_documentation.md](v1/docs/v1_documentation.md) |
| v2 | [v2/README.md](v2/README.md), [v2/docs/v2_documentation.md](v2/docs/v2_documentation.md), [v2/TheGreatRetrofit_v2.ipynb](v2/TheGreatRetrofit_v2.ipynb) |
| v3 | [v3/README.md](v3/README.md), [model spec](v3/docs/model-spec.md), [placeholders](v3/docs/placeholders.md), [frame schema](v3/docs/frame-schema.md), [audit](v3/docs/audit.md) |
| v3 in the browser | [packs/great-retrofit/README.md](packs/great-retrofit/README.md), [Jette integration check](docs/verification/jette-integration.md) |
| v1 vs v2 | [docs/comparison_report.md](docs/comparison_report.md) |
| Plans | [v2 upgrade plan](docs/plans/2026-11-03-model-upgrade.md), [v3 interactive retrofit plan](docs/plans/2026-11-06-interactive-retrofit-plan.md), [original upgrade plan](Joffa's%20original/upgrade%20plan.md) |
| Calibration data | [docs/calibration/](docs/calibration/README.md) |
| Defects and open questions | [docs/state-machines.md](docs/state-machines.md), [docs/design-questions.md](docs/design-questions.md) |

## Parameter sweeps (v1, v2)

```bash
python scripts/run_sweep.py --quick --version both --out data/sweep.csv
python scripts/plot_results.py --v1 data/sweep.v1.csv --v2 data/sweep.v2.csv --out plots/
```

A v3 sweep (needed for equal-public-cost comparisons and the sensitivity view) is not written yet.
