# Placeholders in v3

Every value below is a stand-in, chosen only so the structure runs and the tests are meaningful. **None is calibrated or sourced.** No regressivity or other substantive result may be quoted from runs on these defaults. "Q" refers to the numbered open questions held outside this repository.

A test (`test_docs_sync.py`) fails if a `# PLACEHOLDER` in `params.py` / `scene_entities.py` is missing here, or the reverse.

| Name | Default | Meaning (from code) | Awaiting |
|---|---|---|---|
| `deduction_rate` | 0.3 | share of cost deductible from tax | Q2 |
| `refundable` | False | refundable-credit toggle | Q20 |
| `rebate_lag_months` | 12 | months until the rebate arrives | Q2 |
| `credit_access` | "income_tested" | income_tested | open | none | Q3 |
| `loan_rate` | 0.04 | annual loan rate | Q3 |
| `delivery_mode` | "rebate_market" | rebate_market | passthrough | public_service | Q5 |
| `vendor_margin` | 0.15 | market vendor margin over base cost | Q5 |
| `public_overhead` | 0.10 | public service overhead over base cost | Q5 |
| `public_capacity` | 0.05 | max share of all units the service completes per year | Q5, Q15 |
| `means_test` | False | restrict all delivery modes (rebate, passthrough, public_service) by income quintile; outside it: market purchase, no subsidy | Q5, Q20 |
| `means_test_max_quintile` | 2 | highest quintile eligible when means_test | Q5 |
| `energy_scenario` | "rising" | flat | rising | shock | Q9 |
| `peer_effect` | True | condo: a neighbour's retrofit raises the chance of following (off: `neighbour_boost` is ignored) | Q8 |
| `loan_rate_risk_premium` | 0.02 | extra annual loan rate for households below `credit_income_threshold` (only matters when credit is `open`) | Q3 |
| `shared_measure` | True | condo buildings with 2+ units have shared parts (windows, facade, roof) that need a vote | Q13, Q14 |
| `shared_share` | 0.4 | share of retrofit cost, and of the energy saving, that sits in the shared parts | Q13, Q9 |
| `vote_threshold` | 2/3 | floor-area share that must vote yes; the figure is the two-thirds rule from a secondary source (Civil Code art. 3.88), unverified | Q13 |
| `canvass_target_hours` | 2.0 | weekly hours an advocate would spend canvassing, capped by free time | Q7 |
| `canvass_boost` | 0.2 | extra monthly consideration chance at full canvassing pressure (condo) | Q7 |
| `canvass_saturation_hours` | 6.0 | weekly canvassing hours of the other advocates in a building that give full pressure | Q7 |
| `waking_hours_per_week` | 112.0 | 16 waking hours x 7 days | Q7 |
| `committed_hours_per_week` | 50.0 | chores, commuting, care: neither work nor free | Q7 |
| `work_hours_by_quintile` | (42, 38, 36, 40, 48) | weekly working hours, income quintile 1 to 5 (long at both ends, by design of the question, not from data: the survey found no hours by income) | Q7 |
| `free_time_spread` | 0.3 | +/- relative spread of free hours across households | Q7 |
| `energy_growth_flat` | 0.0 | annual real growth of savings value | ? |
| `energy_growth_rising` | 0.03 |  | ? |
| `energy_growth_shock` | 0.08 |  | ? |
| `cost_per_m2` | 300.0 | base cost (labour+materials) per m2 | Q9 |
| `saving_per_m2_year` | 20.0 | annual energy bill saving per m2 at today's prices | Q9 |
| `discount_rate` | 0.04 | annual discount rate | Q6 |
| `consider_prob_base` | 0.05 | monthly chance a household considers retrofitting | Q6, Q8 |
| `neighbour_boost` | 0.30 | extra consideration chance, times share of building adopted (condo) | Q8 |
| `savings_usable_share` | 1.0 | share of savings available for the retrofit | Q6 |
| `credit_income_threshold` | 25000.0 | income needed under income_tested | Q3 |
| `credit_loan_to_income` | 1.0 | loan cap as multiple of annual income | Q3 |
| `loan_term_months` | 120 |  | Q3 |
| `income_log_mean` | 10.3 | ln(annual income), ~ 30k | Q17, Q18 |
| `income_log_sd` | 0.5 |  | Q17, Q18 |
| `tax_rate` | 0.25 | flat rate above allowance | Q2, Q17 |
| `tax_free_allowance` | 10000.0 |  | Q2, Q17 |
| `savings_months_of_income` | 3.0 | mean liquid savings in months of income | Q6, Q17 |
| `savings_scale` | 1.0 | multiplier on savings (0 = zero-savings world) | Q6 |
| `savings_log_sd` | 0.8 |  | Q17 |
| `years_in_dwelling_min` | 5.0 |  | Q6, Q16 |
| `years_in_dwelling_max` | 25.0 |  | Q6, Q16 |
| `usable_fraction` | 0.8 | share of gross area that is dwelling floor | Q12 |
| `avg_unit_area` | 80.0 | m2 per dwelling unit | Q12 |
| `rental_share_single` | 0.10 | share of single-unit buildings that are rented (scene rule; also a run parameter, see "Tenure rule") | Q4 |
| `rental_share_multi` | 0.30 | share of multi-unit buildings that are rental (scene rule; also a run parameter) | Q4 |
| `unit_area_spread` | 0.2 | +/- relative spread of unit sizes in a building | Q12 |

## Tenure rule (placeholder)

Which scene buildings are owner-occupied, condo or rental is **not data**. Rule (`scene_entities.build_entities`, `SceneRules`): a building with one dwelling unit is rental with probability `rental_share_single`, else owner-occupied; a building with two or more is rental with probability `rental_share_multi`, else condo. "Probability" is a fixed per-building uniform draw from the scene seed, stored on the model building (`rental_draw`), so the same building keeps the same draw. With the defaults 0.10 and 0.30 and the Jette scene, this gave 45% condo, 31% owner-occupied and 23% rental of 8,105 buildings (the integration check); that outcome follows from the two shares and the unit-count rule, nothing else.

The two shares are also **run parameters** (`Params.rental_share_single` / `rental_share_multi`, defaults 0.10 and 0.30, same as the scene rules, so nothing changes unless they move; `None` keeps what the scene rules gave; the pack sets them from its sliders). When set, each scene-built building is re-assigned from its stored draw, so moving the slider changes which buildings are rental without re-binding the scene; buildings given explicit tenure (tests) are untouched. The frame reports the outcome as `series.tenure_counts`. Rental buildings are `not_modelled` (grey): they never adopt, and every share in the output has them in its denominator.

Candidate figures for the economists (from `docs/calibration/tenure-and-buildings.md`; **none is used in the model**, and none is a share of *buildings*, which is what the rule needs):

| Candidate | Value | Confidence | Why it does not fit directly |
|---|---|---|---|
| Owner-occupied share of dwellings, Jette, Census 2011 (IBSA) | 48% | medium (2011; no Jette 2021 figure found) | share of dwellings, not buildings; the rest (52%) mixes private and social tenants |
| Owner-occupied share of dwellings, Brussels Region, Census 2021 | 38.12% | high (region only) | region, not Jette |
| Owner-occupancy: houses 76.9% vs apartments 31.6% (Region) | | low (search summary only) | would suggest a rental share that depends on building type, which the rule's unit-count split approximates |
| Social dwellings, Jette, end 2020 | 1,406, 6.3 per 100 households | high | social landlords are a different actor from the private landlord the stub will model |
| Apartment buildings among Jette residential buildings, 2021 | 23% | high | gives the share of multi-unit buildings, not their tenure |

The rule's 45% condo share is therefore **not** a finding about Jette's co-ownership; the calibration doc found no commune-level co-ownership count.

## Structure that is stubbed or absent (not parameters)

- **Rental buildings:** stub (`ownership.Rental`); state `not_modelled`, never adopt (Q4, Q11).
- **Condo shared parts:** implemented as a vote (see `model-spec.md`), with these structural simplifications awaiting Q13, Q14: votes weighted by floor area; supporters are households whose own NPV for their share is positive and financeable; the measure passes only if **every** owner can finance their share (no collective loan, no reserve fund); once passed, every owner pays; shared measures use no public-service capacity.
- **Canvassing / time budget:** implemented for condo buildings (see spec). Only advocates canvass; effect is on the consideration chance of other households in the same building; free hours are static over time (Q7).
- **Moving, death, inheritance:** none; a household stays for `years_in_dwelling` and then stops considering (Q16). A household past its horizon still owes its share of a shared measure that passes later.
- **Rebate carry-forward / spreading:** none; one deduction against one year's tax, shared by all the household's payments (Q2).
- **Means test** applies to all three modes; a household outside it buys on the market at the vendor price with no subsidy (Q5, Q20).
- **Energy price path:** constant annual growth per scenario; households have perfect foresight of it; "shock" is a higher growth rate, not an unexpected jump.
- **Loan subsidy and loan interest costs to the state:** not counted in `public_cost` (Q19).
- **Delivery vendor capacity:** unlimited for market modes (Q15).
