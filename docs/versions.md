# Model versions: v1, v2, v3

This repository holds three models of housing retrofit in Brussels. They are not three drafts of one model. v1 and v2 ask how retrofit **co-ops** get work done and stay solvent. v3 asks a different question: **which households retrofit at all**, and what the state pays to make it happen. This page sets out what each version added, what it dropped, and what each feature means in plain terms.

Version docs: [v1](../v1/README.md) · [v2](../v2/README.md) · [v3](../v3/README.md). Earlier comparison of v1 and v2: [comparison_report.md](comparison_report.md).

## At a glance

| | v1 | v2 | v3 |
|---|---|---|---|
| **Question** | How fast can co-ops with limited capital work through a queue of buildings? | The same, with heterogeneous owners, banks, neighbourhoods and a changing population | Given who can pay, who gets the subsidy and how the work is delivered, which households retrofit, and what does the state spend? |
| **Paradigm** | Queueing and cash flow | Agent-based market | Agent-based household decision (NPV plus ability to finance) |
| **Time step** | Week | Week | Month (default 180 months = 15 years) |
| **Who decides** | Nobody: buildings request at a Poisson rate | Households request with a personal probability; co-ops and banks respond | Each household, by NPV and financing; condo owners also vote on shared parts |
| **Map** | None | Abstract neighbourhoods | Real building footprints of Jette (Brussels) |
| **Runs in** | Python | Python, plus a notebook | Python (reference), JavaScript in the browser, NetLogo |
| **Parameters** | Illustrative | Illustrative | Explicitly placeholders, each listed with the open question it waits on |
| **Status** | Frozen | Frozen (reference for the co-op market) | Active |

## Origin: Joffa's original → v1

`Joffa's original/GreatRetroFit.ipynb` is the prototype. **v1 is a faithful port of that notebook into a tested Python package**, with no new mechanism. The port was done so that later changes could be tested against a known baseline.

What v1 models:

| Feature | What it means |
|---|---|
| Four building states: `to_do → queued → in progress → finished` | Every building is somewhere in a pipeline; the count in all four always sums to `n` |
| Poisson requests (`tau` per week) | Demand is one aggregate number, not a decision by anyone |
| Co-ops as cash accounts (endowment `E`) | A co-op takes a project only if its account covers all current projects plus the new one: **capital is the only bottleneck**, labour is unlimited |
| Surplus on completion (`surplus`) | Each finished job returns `(1 + surplus) × cost`, so co-op capital compounds |
| Random durations (`mean_time ± time_var`) | Cash flows are staggered; projects do not all finish together |

What v1 can tell you: how queue length and co-op capital interact under different request rates and surpluses. What it cannot: anything about who the owners are or why they ask for a retrofit.

## v1 → v2: from a queue to a market

v2 keeps v1's pipeline and co-ops (all ten v1 parameters carry over) and adds the 23 items of `Joffa's original/upgrade plan.md`, adapted from a housing market to a retrofit market. Many are behind switches that are off by default (bargaining, default, investors, construction, demographics, local demand), so each can be turned on alone. v2 still draws households, so it is not a drop-in copy of v1 even with every switch off.

| Added in v2 | What it means |
|---|---|
| **Households** with income (lognormal), wealth (Pareto, independent of income), age, aspiration, taste weights | Owners differ: a rich, impatient owner and a poor, reluctant one now behave differently |
| **Aspiration-driven requests** | Each owner asks for a retrofit with their own weekly probability, instead of one market-wide Poisson rate |
| **Building attributes**: size, age, location quality, neighbourhood, condition | Retrofit time and cost scale with the building; buildings are no longer interchangeable |
| **Limited search** (`search_length`) | An owner sees only a few co-ops, so demand does not pile onto the same ones |
| **Bargaining** | Buyers bid below asking, sellers have a reservation price; some negotiations fail |
| **Banks** with different loan-to-value caps and spreads, risk-based pricing, a 30% payment-to-income cap | Co-ops borrow for part of their projects; credit is priced and can be refused |
| **Default and foreclosure** (50% recovery) | A borrower who cannot pay now hits the bank's balance sheet, so losses can spread |
| **Bank adaptation** | Banks tighten after losses and loosen after price growth: the mechanism behind credit cycles |
| **Income process**: AR(1) log income plus unemployment spells | Incomes move during the run; a household can fall into difficulty |
| **Neighbourhoods and local demand** | Time on market is tracked per neighbourhood, so a hot area and a cold area can diverge |
| **Investors** (15% landlords with a hurdle rate) | Some owners buy when yield plus growth beats their required return |
| **Demographics**: births, deaths, inheritance | The population turns over, so the system does not settle into a steady state |
| **Depreciation and new construction** | Buildings degrade (retrofitted ones more slowly); new ones are built when price exceeds 1.2 × build cost |
| **Monitors**: wealth Gini, price dispersion (within and between neighbourhoods), cash-buyer share, time-on-market spread, bank losses, defaults, population | Outputs about inequality, segmentation and financial stability, not just throughput |

Known limitations of v2 (its [documentation](../v2/docs/v2_documentation.md#known-limitations) and the [v3 plan](plans/2026-11-06-interactive-retrofit-plan.md)): transaction and moving costs are defined but unused; expectations affect only investors; wealth tends to drain to zero; the "finished" count is ambiguous; nothing is calibrated.

## v2 → v3: a new question, a new model

The policy question changed to **why do tax rebates on retrofits work poorly, and why are they regressive?** v2 cannot answer it. It has no retrofit-or-not decision (owners queue for work; nobody weighs whether the work pays), and no buildings with several households in them. So v3 is a new package, not an extension. v2 stays frozen as the reference for the co-op market ([plan](plans/2026-11-06-interactive-retrofit-plan.md), decision D1).

v3 is **economic, not social**: households retrofit when the money works over the time they expect to stay and they can finance it. There is no ideology premium and no preference for being green. Regressivity is meant to *emerge* from credit access and tax capacity, not be assumed.

### Dropped from v2

Co-ops and their capital accounts, multiple banks, bargaining, search, investors, construction, depreciation, demographics (births, deaths, inheritance), the AR(1) income process, and the weekly step. Rental buildings are kept only as a stub (shown, never modelled). These may come back if the economists ask for them; v2's bank and co-op modules can be borrowed.

### Added in v3: the model

| Added in v3 | What it means |
|---|---|
| **NPV decision over the stay horizon** | A household retrofits only if discounted bill savings plus any rebate exceed what it pays (cash from savings plus the discounted loan payments), counted only for the years it expects to stay. A household that will move in five years values the work less than one staying twenty-five |
| **Ability to finance** | The upfront cost is paid from savings first, then a loan up to a credit limit. A positive NPV is not enough: if the household cannot raise the money, it does not retrofit |
| **Household tax payable** | Computed from income. It caps what a non-refundable rebate can give back. This is one of the two regressivity channels |
| **Credit access rules**: `income_tested`, `open`, `none`; risk premium below an income threshold | Who can borrow, and at what rate. This is the other regressivity channel |
| **Three delivery modes** | (a) **rebate with a market vendor**: the household pays everything now and gets part back later; (b) **pass-through**: the state pays the vendor directly, the household pays nothing; (c) **public service**: the state does the work at cost plus overhead, no profit, but with limited capacity |
| **Rebate rules**: deduction rate, refundable or not, lag in months, tax capacity used up across payments | How generous the rebate is, whether people with no tax to pay get anything, and how long they wait for it |
| **Means test**, all three modes | Only the lower income quintiles are in the scheme; everyone else can still buy on the market, unsubsidised |
| **Three ownership types**: owner-occupied, condo, rental (stub) | Who decides: a single owner, each condo owner for their own unit, or a landlord (not yet modelled, shown grey) |
| **Condo shared-part vote** | Windows, facade and roof belong to everyone. Owners support the work if their share pays for them; it passes at a floor-area threshold (default two-thirds), but only if every owner can pay. Once passed, everyone pays, supporters or not |
| **Neighbour effect** (`peer_effect`) | In a condo, each unit retrofitted raises the chance the others consider it |
| **Canvassing as a weekly time budget** | Advocates spend free hours persuading neighbours. Free hours come from working hours by income quintile, so time-poor households (long hours at both ends of the income scale, by hypothesis) canvass less |
| **Energy price scenarios**: flat, rising, shock | How fast the value of bill savings grows. Households know the path in advance |
| **Monthly timing with a start-of-month snapshot** | Nobody reacts to a decision made in the same month, so the order in which households are processed does not change the result |
| **Per-quintile outputs** (the five policy views) | (1) household net cash over time; (2) public transfer per euro of price; (3) share able to pay the price now; (4) adoption; (5) cost per retrofit split into base cost and margin or overhead. Plus public cost and bills saved |
| **Placeholder discipline** | Every default is listed in [placeholders.md](../v3/docs/placeholders.md) with the open question it waits on; a test fails if a placeholder in the code is missing from the list. No result may be quoted from the defaults |

### Added in v3: running it on a real map, in a browser

| Added in v3 | What it means |
|---|---|
| **Model from the scene** (`scene_entities.py`, `bind.js`) | Buildings come from real Jette footprints (OSM): floor area from footprint × storeys, dwelling units from floor area. Tenure and unit counts are placeholder rules, not data. Households are synthetic |
| **JavaScript port** (`packs/great-retrofit/runtime.js`) | The model runs live in the page: move a slider, the 15-year run on 8,105 Jette buildings is redone in about a second |
| **Shared PRNG** (mulberry32, `hash_uniform`) in Python, JS and NetLogo | The same seed gives the same history in every language. Per-household, per-month draws are stateless, so changing one policy lever never reshuffles other households' luck (common random numbers) |
| **Parity tests** (24 golden trajectories) | Python and JavaScript must produce the same frames, exact for counts and states, to 1e-9 for money |
| **Frame schema** ([frame-schema.md](../v3/docs/frame-schema.md)) | A versioned contract for what the model emits each month, so the page and the model can change independently |
| **paperdolls model pack** (`packs/great-retrofit/`) | A manifest of sliders, presets, colour mappings, charts and KPIs that the paperdolls viewer turns into the interactive page |
| **NetLogo port** (`v3/great-retrofit-v3.nlogox`) | A single-file NetLogo 7 version for people who prefer to explore there: same rules, same PRNG, sliders for every lever. Its Info tab documents it |
| **Geodata pipeline** (`scripts/geodata/`) | Optional: real terrain (UrbIS 1 m DTM) and measured building heights (UrbIS 3D) instead of assumed storeys |
| **Calibration survey** ([docs/calibration/](calibration/README.md)) | What public data exists for Jette and Brussels for each parameter, with evidence tags. Survey only; nothing in the model uses it yet |
| **Defect hunt and fuzzing** ([state-machines.md](state-machines.md), `tests/fuzz/`) | State machines of the model and runtime, confirmed defects with regression tests, and three design questions left open ([design-questions.md](design-questions.md)) |

## Feature matrix

✓ = modelled, — = absent, *stub* = present but inert.

| Feature | v1 | v2 | v3 |
|---|:-:|:-:|:-:|
| Building pipeline / states | ✓ | ✓ | ✓ (not / partly / fully retrofitted, not modelled) |
| Co-ops with capital constraint | ✓ | ✓ | — |
| Heterogeneous households (income, savings) | — | ✓ | ✓ |
| Household decides whether to retrofit | — | — (requests by aspiration) | ✓ (NPV + financing) |
| Stay horizon | — | — | ✓ |
| Tax payable / rebate | — | — | ✓ |
| Credit | — | ✓ (banks lend to co-ops) | ✓ (one lender, households borrow) |
| Default, foreclosure, bank adaptation | — | ✓ | — |
| Delivery modes (rebate / pass-through / public service) | — | — | ✓ |
| Means test | — | — | ✓ |
| Multi-unit buildings, condo vote | — | — | ✓ |
| Neighbour effect, canvassing | — | — | ✓ |
| Rental / landlords | — | ✓ (investors) | *stub* |
| Neighbourhoods | — | ✓ (abstract) | real map, same-building effects only |
| Bargaining, search | — | ✓ | — |
| Income dynamics, demographics | — | ✓ | — |
| Depreciation, new construction | — | ✓ | — |
| Energy price scenarios | — | — | ✓ |
| Outputs by income quintile | — | — | ✓ |
| Inequality / market monitors (Gini, dispersion) | — | ✓ | — |
| Browser runtime with live sliders | — | — | ✓ |
| Same results across languages | — | — | ✓ (Python = JS, tested; NetLogo ported) |

## What each version can claim

- **v1**: mechanical properties of a capital-constrained queue (conservation, monotone completion, compounding with surplus).
- **v2**: how its added mechanisms interact, on illustrative parameters. Not calibrated to Brussels.
- **v3**: only *structure*: which channels are open or closed under which levers, and internal consistency (a rebate never exceeds cost or tax payable; the public service never exceeds capacity; a vote never passes below threshold; Python and JS agree). It **cannot** claim any regressivity result, level, or ranking of delivery modes until the economists replace the placeholders and the sensitivity sweep exists. See [model-spec.md §10](../v3/docs/model-spec.md#10-what-the-model-can-and-cannot-claim).
