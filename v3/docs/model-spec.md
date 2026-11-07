# The Great Retrofit, model v3: specification

Status: draft for the economists to read and correct. It describes what `v3/src/retrofit_v3/` and its JavaScript port (`packs/great-retrofit/runtime.js`) do **today**, after the mechanics work recorded in [audit.md](audit.md). It is written so that a rule you disagree with can be pointed at by name (the bold names below are also the names in the code).

**Every number in this model is a placeholder.** The defaults exist so the structure runs and the tests mean something. They are listed in [placeholders.md](placeholders.md) with the open question each one waits on. Nothing computed from them is a finding (see §9).

Contents: 1 purpose and scope; 2 state; 3 timing; 4 household decision; 5 ownership rules; 6 delivery modes; 7 rebate, credit and means test; 8 outputs; 9 assumptions table; 10 what the model can and cannot claim; 11 what is not modelled.

## 1. Purpose and scope

A model of **household retrofit decisions** in a commune (Jette, Brussels) on a real building map. It asks one question: *given who can pay, who gets the subsidy, and how the work is delivered, which households retrofit, and what does the state spend?* It is **economic, not social**: households retrofit when the money works over the time they expect to stay, and when they can finance it. There is no ideology premium, no solidarity lever, no preference for being green. Regressivity is meant to *emerge* from credit access plus tax capacity, not be assumed.

In scope: owner-occupied homes and condo units (decision by each owner; shared parts by a vote). Out of scope: rental buildings (stub: shown on the map as "not modelled", never retrofit), energy communities, new construction, moving and inheritance.

Time step: one month; the default horizon is 180 months (15 years). The model is stochastic (a household only *considers* retrofitting with some monthly chance) but deterministic given the seed: the same seed gives the same history, in Python and in JavaScript.

## 2. State

### Buildings (from the map)
Each modelled building has a **tenure** (`owner_occupied`, `condo`, `rental`) and a list of **dwelling units**, each with a floor area `area_i` (m²). The synthetic scene rules (`scene_entities.py`) turn map footprints into units: gross floor area = footprint × storeys × `usable_fraction`; units = gross / `avg_unit_area`, rounded; a building is rental with probability `rental_share_single` (one unit) or `rental_share_multi` (more), otherwise owner-occupied (one unit) or condo (more). Which tenure and how many units a building gets is the model's guess, not data.

### Households (one per dwelling unit, drawn at the start)
| Variable | Meaning | Drawn as |
|---|---|---|
| `income_i` | annual income | lognormal(`income_log_mean`, `income_log_sd`) |
| `quintile_i` | income quintile 1..5 over all units in the scene | rank of income |
| `tax_i` | tax payable per year | `max(0, tax_rate × (income − tax_free_allowance))` |
| `savings_i` | liquid savings | lognormal(0, `savings_log_sd`) × `savings_scale` × `savings_months_of_income` × income / 12 |
| `horizon_i` | months the household expects to stay | uniform(`years_in_dwelling_min`, `_max`) × 12, rounded |
| `free_i` | weekly free hours (the time budget) | see §5.3 |
| `tax_left_i` | tax capacity not yet used by a rebate | starts at `tax_i` |
| `credit limit` | what the household may borrow | `credit_access` rule (§7.2) |

A household stops considering retrofits after `horizon_i` months.

### Other state
Per building: how many units are fully retrofitted, whether a shared measure is pending or approved. Per household: whether its own part and its share of a shared part are paid, whether it **supports** the shared measure, its loans, its cumulative cash. Global: a list of rebates due in future months, public-service capacity carried between months.

## 3. Timing within a month `t`

1. **Cash.** Rebates due at `t` reach households and are added to the state's cumulative cost (the state pays when the rebate arrives, not at adoption). Loan payments fall due. Households that have retrofitted something (and are still within `horizon_i`) accrue their energy bill savings.
2. **Snapshot.** Building adoption shares and canvassing hours are read as they stood at the start of the month. Nobody reacts to a decision taken in the same month; this makes the order of households irrelevant.
3. **Consideration.** Each household that is not finished, can adopt, and is within its horizon *considers* with probability `p_consider` (§5). A draw `hash_uniform(seed, household, month)` decides, so changing a policy lever never reshuffles the draws of other households (common random numbers). A household that considers: (a) if its own part is unpaid, evaluates it (NPV and financing, §4); if both pass, it is a **candidate**; (b) if its building has a shared measure not yet approved and it does not already support it, evaluates its share of the shared measure the same way; if both pass, it becomes a **supporter** (permanently, until the vote).
4. **Capacity and payment.** In `public_service` mode the candidates who use public capacity are ranked by a fixed random draw and only as many as this month's slots are accepted. All accepted candidates pay for their own part.
5. **Votes.** For each building with a pending shared measure: if the floor-area share of supporters is at least `vote_threshold`, and every owner in the building can finance their share, and (public service only) enough slots are left, the measure is approved and **every** owner pays their share this month.
6. **Frame.** The state is read out (§8).

## 4. Household decision

A household retrofits (pays for a part) when two conditions hold.

**Financeable.** The upfront amount `U` is paid from savings first (`usable = savings × savings_usable_share`), the rest by a loan `L = U − min(usable, U)`. It is feasible if `L ≤ credit_limit`. In `passthrough` and `public_service` (for households inside the scheme) `U = 0`: always feasible.

**NPV positive.** With monthly discount rate `r = (1 + discount_rate)^(1/12) − 1` and monthly energy growth `g = (1 + energy_growth)^(1/12) − 1`:

```
NPV = PV(savings) + PV(rebate) − cash_from_savings − PV(loan payments)

PV(savings)       = Σ_{k=1..n}  s · (1+g)^(k−1) · level_t / (1+r)^k          n = horizon_i − t
                    s = area_i · saving_per_m2_year / 12 · saved_fraction
                    level_t = (1+g)^t     (energy price level at month t, 1 at t = 0)
PV(rebate)        = rebate / (1+r)^lag
PV(loan payments) = Σ_{k=1..term} pay / (1+r)^k
                    pay = level annuity of L at the household's loan rate over loan_term_months
```

The loan principal is not a separate term: it funds the price, and the household's cost of that part is the discounted stream of payments. The household knows the energy price path of its scenario exactly (perfect foresight). It values nothing beyond its own horizon: no resale value of a better house. Savings are only counted while the household is expected to live there.

`saved_fraction` is 1 for a whole retrofit; for a condo with a shared measure it is `1 − shared_share` for the unit part and `shared_share` for the shared part (cost and saving are split in the same proportion, a simplification).

The **loan rate** is `loan_rate`, plus `loan_rate_risk_premium` if `income < credit_income_threshold` (household-dependent rate; only matters when credit is `open`, because an income-tested lender would not lend to that household at all).

## 5. Ownership rules

### 5.1 Owner-occupied home
The household decides alone. `p_consider = consider_prob_base` each month. The cost is the whole retrofit: `base = area × cost_per_m2`.

### 5.2 Condo unit
Each owner decides for their unit.

**Neighbour effect (`peer_effect`).** `p_consider = min(1, consider_prob_base + neighbour_boost × a_b + canvass_boost × c_i)` where `a_b` is the share of units in the building fully retrofitted at the start of the month and `c_i` is canvassing pressure (§5.3). With `peer_effect` off, the `neighbour_boost` term is dropped. "Neighbour" means the same building only (an assumption).

**Shared measure (`shared_measure`).** A condo building with at least two units has shared parts (windows, facade, roof). When `shared_measure` is on, the retrofit of a unit has two parts:
- the **unit part**: `base = area_i × cost_per_m2 × (1 − shared_share)`, decided by each owner alone (steps 3 and 4);
- the **shared part**: building total `S = shared_share × cost_per_m2 × floor_area`, split among owners **by floor area**: owner `i` pays base `S × area_i / floor_area`.

A unit counts as retrofitted when both parts are paid. The shared part is decided by a vote:
- *Support.* When a household considers, it evaluates its own share (NPV with `saved_fraction = shared_share`, and financing). If both pass, it supports. Support is permanent.
- *Weight.* Votes are weighted by floor area (a proxy for the "quotités" of Belgian co-ownership law); `yes_share = Σ area of supporters / floor_area`.
- *Passing.* The measure passes in the first month where `yes_share ≥ vote_threshold`, provided every owner in the building can finance their share at that moment (savings and credit, or the state pays). Otherwise it stays pending; a single owner who cannot pay blocks it (no collective loan, no reserve fund: an assumption awaiting Q13/Q14).
- *Consequence.* Once passed, every owner pays their share, supporter or not, financed by their own savings and credit under the active delivery mode. Households that did not support the measure pay too; their NPV is not checked.
- *Default.* `vote_threshold = 2/3` of floor area, from a secondary source for Civil Code art. 3.88 (works on common parts: two-thirds of votes). Not verified at the source (see `docs/calibration/tenure-and-buildings.md`).

### 5.3 Canvassing as a weekly time budget
Each household has a weekly time budget `free_i` of hours neither worked nor committed:

```
free_i = max(0, waking_hours_per_week − committed_hours_per_week − work_hours_by_quintile[quintile_i]) × (1 + free_time_spread × (2u − 1))
```
with `u` a fixed uniform draw per household (so the budget is static; the spread keeps households of one quintile different). The default working hours are long at both ends of the income scale and shorter in the middle, by construction (to test the structure: the calibration survey found no source for hours by income).

Only **advocates** canvass: households that support a pending shared measure or have paid for any part. An advocate in a co-owned building spends `spend_j = min(free_j, canvass_target_hours)` hours a week. A household with less free time spends less. Spending is limited by the budget, so the leisure left is never negative.

The pressure a household feels from its neighbours is `c_i = min(1, (Σ_{advocates j in building, j ≠ i} spend_j) / canvass_saturation_hours)`. It raises `p_consider` by `canvass_boost × c_i` (§5.2). Canvassing therefore raises the chance a neighbour follows or turns up as a supporter; it never forces a vote. Canvassing only happens in co-owned buildings, and the effect is within the building.

### 5.4 Rental building
Stub. Marked `not_modelled`, never adopts, never votes. The household rows of rental units exist (they count in quintile denominators) but do nothing.

## 6. Delivery modes

A **quote** for a part with base cost `B` returns: price, what the household must finance now, what the state pays now, the rebate and its lag, and whether the part uses public capacity.

| Mode | Price | Household pays now | State pays | Notes |
|---|---|---|---|---|
| `rebate_market` (a) | `B × (1 + vendor_margin)` | all of it (savings, then credit) | rebate later (§7.1) | Credit access and tax capacity decide who can use it. |
| `passthrough` (b) | `B × (1 + vendor_margin)` | nothing | the whole price at once | No credit needed. Market vendor margin applies. |
| `public_service` (c) | `B × (1 + public_overhead)` | nothing | the whole price at once | No profit. Capacity-limited (below). |

**Public capacity.** The service completes at most `public_capacity × (number of units) / 12` slots a month; the fractional part carries to the next month, whole unused slots are lost. Each unit (or whole) retrofit uses one slot. A shared measure uses `ceil(units × shared_share)` slots, taken from what is left after the unit parts of the same month. When more households want a slot than there are slots, a fixed random draw per household orders the queue. The market modes have unlimited vendor capacity.

## 7. Rebate, credit and means test

### 7.1 Rebate (mode a)
```
gross  = deduction_rate × price
rebate = min(gross, price)                          if refundable
       = min(gross, price, tax_left_i)              otherwise
```
The rebate arrives `rebate_lag_months` after the payment: lag 0 is paid in the month of the payment (it shows in the frame that step emits), lag L >= 1 in month t + L. A fractional lag is rounded half to even to whole months by `Params`. `tax_left_i` is reduced by each rebate granted, so a household's one year of tax capacity is shared among all its payments (own part and shared part); there is no carry-forward to later years. The non-refundable cap is the **tax-capacity channel** of regressivity; credit access (7.2) is the other.

### 7.2 Credit access
| Rule | Credit limit |
|---|---|
| `income_tested` | `credit_loan_to_income × income` if `income ≥ credit_income_threshold`, else 0 |
| `open` | `credit_loan_to_income × income` |
| `none` | 0 |

One bank. Loans are level annuities over `loan_term_months`. The state pays nothing for loan interest or for default (not counted).

### 7.3 Means test (`means_test`)
If on, only households in income quintiles `1..means_test_max_quintile` are inside the public scheme, in every mode: for `rebate_market` they get the rebate, for `passthrough` and `public_service` the free work. A household outside buys on the market: price `B × (1 + vendor_margin)`, financed from its own savings and credit, no rebate, no state payment, no public capacity. (Before this branch, such a household could not retrofit at all; see audit row 11.)

### 7.4 Energy price scenarios
`energy_scenario ∈ {flat, rising, shock}` picks a constant annual growth in the value of energy savings (`energy_growth_flat`, `_rising`, `_shock`). The "shock" is a higher growth, not an unexpected jump.

## 8. Outputs

The frame schema is [frame-schema.md](frame-schema.md); here is what each series means.

| Series | Definition |
|---|---|
| `adoption_by_quintile[q]` | retrofitted units in quintile `q` / units in `q` (rental included in the denominator) |
| `rebate_per_euro[q]` | (state payments at adoption + rebates entitled) / price, over payments by households of `q` so far. In mode a, below 1 and falls with tax capacity; in b and c, 1 for households inside the scheme |
| `can_front_cost[q]` | among not-retrofitted modelled units in `q`: share who could finance now what they still owe (savings plus credit; 1 inside a state-funded scheme) |
| `cost_per_retrofit` | mean total price paid per retrofitted unit so far (own part plus its shared part) |
| `cost_per_retrofit_parts` | `{base, markup}`: mean base cost and mean vendor margin or public overhead over the same units; `base + markup = cost_per_retrofit` |
| `public_cost` | cumulative euros paid by the state: payments to vendors at adoption, rebates when they arrive |
| `bills_saved` | cumulative household energy bills saved |
| `net_cash_by_quintile[q]` | household cash timeline: mean over households that have paid for works of (bills saved + rebates received − savings spent − loan payments made) |
| `canvass_hours_by_quintile[q]`, `leisure_hours_by_quintile[q]` | mean weekly hours spent canvassing / left free, per household of quintile `q` |
| `shared_counts` | condo buildings with a pending / approved shared measure |
| per building | `state` (not retrofitted / partial / retrofitted / not modelled), `adopted_share`, `shared_state`, `vote_yes_share`, `income_q_mean` |

The plan's five views map to: (1) `net_cash_by_quintile`; (2) `rebate_per_euro`; (3) `can_front_cost`; (4) `adoption_by_quintile`, one run per delivery mode at equal public cost (the comparison is made by the caller by running each mode; equal public cost needs a sweep that is not yet written); (5) `cost_per_retrofit` and `cost_per_retrofit_parts`.

## 9. Assumptions table

Status key: **placeholder** = chosen to run, no source; **awaiting economists** = a specific open question must be answered; **from the survey** = a figure from `docs/calibration/` informs it, but the survey's figures are partly unverified (evidence tags `[S]` are search-result summaries that were not opened; statbel.fgov.be and fin.belgium.be were not reachable by the survey's fetcher). "Q" numbers are the numbered open questions held outside this repository.

### 9.1 Parameters
| Assumption (parameter) | Default | Status | Note |
|---|---|---|---|
| `deduction_rate` | 0.3 | placeholder / awaiting economists (Q2) | Actual Belgian/Brussels rule not verified; survey: Renolution (post-works reimbursement, ended 2024) is a premium schedule, not a deduction |
| `refundable` | off | awaiting economists (Q20) | |
| `rebate_lag_months` | 12 | placeholder / from the survey (weak) | Survey: 2024 Renolution backlog took more than a year to pay (`[R]`, one source) |
| `credit_access`, `credit_income_threshold`, `credit_loan_to_income`, `loan_term_months` | income_tested, 25 000, 1.0, 120 | placeholder / awaiting economists (Q3) | Survey found no Belgian data on refusals by income; renovation-loan terms partly unverified (ECORENO 2.5 to 3.5% `[S]`, mortgage rates `[S]`) |
| `loan_rate` | 0.04 | placeholder / from the survey (weak) | Survey figures are 2.5 to 3.5% (renovation loan) and about 3.3% (mortgage, ≥10-year fixed), both `[S]` |
| `loan_rate_risk_premium` | 0.02 | placeholder (Q3) | Introduced by this branch; no source |
| `delivery_mode`, `vendor_margin`, `public_overhead`, `public_capacity` | rebate_market, 0.15, 0.10, 0.05 | placeholder / awaiting economists (Q5, Q15) | Survey: one-stop-shop precedents (Homegrade, Energiesprong) give design, not costs |
| `means_test`, `means_test_max_quintile` | off, 2 | awaiting economists (Q5, Q20) | Market fallback for the excluded is this branch's design choice |
| `energy_scenario`, `energy_growth_*` | rising; 0, 0.03, 0.08 | placeholder / awaiting economists (Q9) | Survey: Eurostat history is solid (`[R]`), forward path is a news summary (`[S]`, low confidence) |
| `cost_per_m2` | 300 | placeholder / awaiting economists (Q9) | Survey: no Brussels cost per m²; only €30 000 to 40 000 per condo unit (INNOVATE 2020, `[R]`) and non-Brussels 290 to 415 €/m² `[S]` |
| `saving_per_m2_year` | 20 | placeholder (Q9) | Survey: modelled (EPC), not measured, savings; no rebound |
| `discount_rate` | 0.04 | placeholder (Q6) | Survey: no source on household discount rates |
| `consider_prob_base`, `neighbour_boost`, `peer_effect` | 0.05, 0.30, on | placeholder / awaiting economists (Q6, Q8) | The channel of the neighbour effect is not confirmed |
| `savings_usable_share`, `savings_months_of_income`, `savings_scale`, `savings_log_sd` | 1.0, 3, 1, 0.8 | placeholder (Q6, Q17) | Survey: no source on savings or wealth |
| `income_log_mean`, `income_log_sd`, `tax_rate`, `tax_free_allowance` | 10.3, 0.5, 0.25, 10 000 | placeholder / from the survey (weak) (Q2, Q17, Q18) | Survey: median Jette taxable income per return €25 678 (2023, `[R]`) against exp(10.3) ≈ €29 700 here; a quarter of returns show under €10 000. The flat tax is not the Belgian schedule (marginal-rate sources were secondary) |
| `years_in_dwelling_min/_max` | 5, 25 | placeholder (Q6, Q16) | |
| `shared_measure`, `shared_share` | on, 0.4 | placeholder / awaiting economists (Q13, Q14) | Cost and saving share assumed equal |
| `vote_threshold` | 2/3 of floor area | from the survey (secondary, unverified) / awaiting economists (Q13) | Civil Code art. 3.88: two-thirds for works affecting common parts; whether energy works count as "imposed by law" (simple majority) is not established; changing how costs are split needs four-fifths |
| `canvass_target_hours`, `canvass_boost`, `canvass_saturation_hours` | 2, 0.2, 6 | placeholder / awaiting economists (Q7) | |
| `waking_hours_per_week`, `committed_hours_per_week`, `work_hours_by_quintile`, `free_time_spread` | 112, 50, (42, 38, 36, 40, 48), 0.3 | placeholder (Q7) | Survey: no hours or leisure by income found (Belgian average usual hours 34.3 in 2025, `[S]`); the U-shape is the plan's hypothesis, not data |
| `usable_fraction`, `avg_unit_area`, `unit_area_spread` | 0.8, 80, 0.2 | placeholder (Q12) | Survey: building type and age (IBSA) exist; unit counts per building do not |
| `rental_share_single`, `rental_share_multi` | 0.10, 0.30 | placeholder / from the survey (weak) (Q4) | Survey: owner-occupied share 38% (Region, Census 2021), 48% (Jette, Census 2011); co-ownership prevalence not found |

### 9.2 Structural assumptions (not parameters)
| Assumption | Status |
|---|---|
| Households maximise the NPV of their own stay; no resale value, no altruism, no habit, no information friction beyond the monthly chance of considering | awaiting economists (Q6) |
| Perfect foresight of the energy price path | placeholder |
| One decision at a time per part; no partial measures, no phasing over years | placeholder |
| One year of tax capacity serves all of a household's payments; no carry-forward | awaiting economists (Q2) |
| A neighbour is someone in the same building; no street or block effect | placeholder (Q8) |
| Votes weighted by floor area; supporters decide by their own NPV; support is permanent | awaiting economists (Q13) |
| A shared measure passes only if every owner can finance their share; once passed, everybody pays; no collective loan or reserve fund | awaiting economists (Q13, Q14) |
| Households past their `horizon` still owe a share of a shared measure that passes later | placeholder |
| Public capacity counts slots; a shared measure uses `ceil(units × shared_share)` slots | placeholder (Q15) |
| Market vendors have unlimited capacity; the vendor margin is exogenous (no price response to demand) | awaiting economists (Q5, Q15) |
| Canvassing only by advocates, only in condos, only within the building; static free hours | awaiting economists (Q7) |
| Households outside a means test buy on the market | placeholder (Q5, Q20) |
| The state's cost excludes loan subsidies, administration outside "overhead", and tax revenue effects (energy-tax losses, extra VAT, jobs) | awaiting economists (Q19) |
| Income quintiles are computed over the scene's households (a commune), not over Belgium | placeholder |
| Rental buildings and energy communities are not modelled | by scope |

## 10. What the model can and cannot claim

**It can claim** (about the *structure*):
- Which mechanisms are in the model and how they interact (this document, and the tests: see `v3/test_v3/test_invariants.py` and `test_mechanics.py`).
- Internal consistency: a rebate never exceeds cost or a household's tax payable; a retrofit paid by the household never exceeds savings plus credit; a shared measure never passes below its threshold or without every owner able to pay; the public service never exceeds its capacity; the time budget is never negative; counts of buildings and units are conserved; a price equals base cost plus markup; a higher subsidy never lowers adoption (with the other levers held fixed, in the market modes); a neighbour effect never lowers adoption; a world with no savings and no credit has no adoption in the market modes. These hold *by construction* and say nothing about the world.
- That the Python and JavaScript implementations give the same trajectories to 1e-9 on the cases in `packs/great-retrofit/tests/cases.json`, under the same seed.
- Directional, *mechanical* statements of the form "in this model, with this lever on, this channel is open or closed" when read off the structure (e.g. a non-refundable rebate is capped by tax payable, so a household with no tax payable gets none).

**It cannot claim:**
- **Any regressivity result from placeholder runs.** Which quintile benefits more, and by how much, depends on the placeholder income, savings, tax and credit numbers. Do not quote adoption by quintile, rebate per euro by quintile, or any comparison of delivery modes from runs on the defaults, in a presentation, a memo or a commit message, as if it were a result. The on-screen banner says so; it must stay.
- Any level: how many Jette households would retrofit, how much the state would spend, how many tonnes of CO₂ are saved, in what year.
- Any ranking of delivery modes. Mode b versus c depends on the vendor margin, the public overhead and the capacity, all placeholders; mode a versus the others depends on credit access and tax capacity, also placeholders.
- Anything about renters, landlords or split incentives; anything about welfare (no utility function; only cash).
- Anything that depends on behaviour the model leaves out: information, trust, disruption, habit, aesthetic or comfort value, rebound, moving, resale value.
- Real-world robustness: the sensitivity view that would show which assumption reverses a result is not built (it needs the sweep script, plan Phase 1).
- That the building map's *tenure* and *unit counts* are right: they are generated by placeholder rules, not read from data. Building geometry is the only real thing on the map.

**Go/no-go reminder (plan Phase 1):** the question "does a rebate-only policy reproduce a regressive pattern, and which lever closes it?" can be answered only once the economists have replaced the placeholders and the sweep exists. Until then the honest answer is "not tested".

## 11. What is not modelled (so nobody looks for it)
Rental buildings and the landlord's incentive; energy communities; households moving, dying, inheriting; mixed tenure within a building; energy-class dependent savings (saving per m² is one number); phasing of works; vendor capacity and price response; credit rationing beyond a rule; the state's budget constraint (public cost is an output, not a limit); learning, advertising or any social influence outside the building; retrofit quality differences between delivery modes.
