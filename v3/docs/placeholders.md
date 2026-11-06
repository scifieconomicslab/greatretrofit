# Placeholders in v3

Every value below is a stand-in, chosen only so the structure runs and the tests are meaningful. **None is calibrated or sourced.** No regressivity or other substantive result may be quoted from runs on these defaults. "Q" refers to [the economist questions](../../docs/plans/2026-11-06-economist-questions.md).

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
| `means_test` | False | restrict passthrough/public_service by income quintile | Q5, Q20 |
| `means_test_max_quintile` | 2 | highest quintile eligible when means_test | Q5 |
| `energy_scenario` | "rising" | flat | rising | shock | Q9 |
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
| `rental_share_single` | 0.10 | share of single-unit buildings that are rented | Q4 |
| `rental_share_multi` | 0.30 | share of multi-unit buildings that are rental | Q4 |
| `unit_area_spread` | 0.2 | +/- relative spread of unit sizes in a building | Q12 |

## Structure that is stubbed or absent (not parameters)

- **Rental buildings:** stub (`ownership.Rental`); state `not_modelled`, never adopt (Q4, Q11).
- **Condo shared-part voting and cost sharing:** not implemented (Q13, Q14). Condo = per-unit decision plus neighbour boost.
- **Canvassing / time budget:** not implemented (Q7).
- **Moving, death, inheritance:** none; a household stays for `years_in_dwelling` and then stops considering (Q16).
- **Rebate carry-forward / spreading:** none; one deduction against one year's tax (Q2).
- **Means test** applies only to passthrough and public_service, not to the rebate (Q5, Q20).
- **Energy price path:** constant annual growth per scenario; households have perfect foresight of it.
- **Loan subsidy and loan interest costs to the state:** not counted in `public_cost` (Q19).
- **Delivery vendor capacity:** unlimited for market modes (Q15).
