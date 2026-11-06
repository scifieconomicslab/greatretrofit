# Energy prices (Belgium) and scenarios

Tags: **[R]** = values read from the Eurostat API on 2026-11-06 (dataset `updated` stamps given); **[S]** = search-result summary only.

## Eurostat household price series (Belgium) — **confidence: high**
- Datasets: `nrg_pc_204` (electricity, household consumers, bi-annual; updated 2026-10-19 23:00) and `nrg_pc_202` (natural gas, household consumers, bi-annual; updated 2026-10-19 11:00). Unit: EUR per kWh. Licence: Eurostat reuse policy (dataset page not opened; confirm at https://ec.europa.eu/eurostat/about-us/policies/copyright). Format: JSON/CSV/TSV via API, e.g.
  - `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204?format=JSON&lang=EN&geo=BE&nrg_cons=KWH2500-4999&unit=KWH&tax=I_TAX&currency=EUR&sinceTimePeriod=2019-S1`
  - `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_202?format=JSON&lang=EN&geo=BE&unit=KWH&tax=I_TAX&currency=EUR&sinceTimePeriod=2019-S1`
- Scope: national average for Belgium, not Brussels-specific. Regional differences (network and levy charges): not quantified here.

### Electricity, band DC (2,500–4,999 kWh/yr), EUR/kWh [R]
| Period | All taxes & levies incl. | Excl. taxes & levies |
|---|---|---|
| 2019-S1 | 0.2839 | 0.1948 |
| 2019-S2 | 0.2860 | 0.1954 |
| 2020-S1 | 0.2792 | 0.1872 |
| 2020-S2 | 0.2702 | 0.1798 |
| 2021-S1 | 0.2702 | 0.1767 |
| 2021-S2 | 0.2994 | 0.2015 |
| 2022-S1 | 0.3437 | 0.2622 |
| 2022-S2 | 0.4489 | 0.3791 |
| 2023-S1 | 0.4350 | 0.3592 |
| 2023-S2 | 0.3778 | 0.2793 |
| 2024-S1 | 0.3354 | 0.2405 |
| 2024-S2 | 0.3313 | 0.2465 |
| 2025-S1 | 0.3571 | 0.2758 |
| 2025-S2 | 0.3499 | 0.2714 |
| 2026-S1 | 0.3575 | 0.2783 |

### Natural gas, EUR/kWh, all taxes and levies included [R]
Band D1 is <20 GJ/yr, D2 20–199 GJ/yr, D3 ≥200 GJ/yr (consumption bands per year).
| Period | D1 (<20 GJ) | D2 (20–199 GJ) | D3 (≥200 GJ) |
|---|---|---|---|
| 2019-S1 | 0.0778 | 0.0554 | 0.0496 |
| 2019-S2 | 0.0890 | 0.0573 | 0.0470 |
| 2020-S1 | 0.0663 | 0.0496 | 0.0440 |
| 2020-S2 | 0.0698 | 0.0498 | 0.0414 |
| 2021-S1 | 0.0640 | 0.0468 | 0.0423 |
| 2021-S2 | 0.0898 | 0.0676 | 0.0640 |
| 2022-S1 | 0.1110 | 0.0943 | 0.0896 |
| 2022-S2 | 0.1458 | 0.1363 | 0.1484 |
| 2023-S1 | 0.1196 | 0.1146 | 0.0957 |
| 2023-S2 | 0.1196 | 0.0994 | 0.0826 |
| 2024-S1 | 0.0976 | 0.0801 | 0.0749 |
| 2024-S2 | 0.1164 | 0.0903 | 0.0824 |
| 2025-S1 | 0.1110 | 0.0919 | 0.0802 |
| 2025-S2 | 0.1183 | 0.0898 | 0.0732 |
| 2026-S1 | 0.1075 | 0.0846 | 0.0726 |

Excluding taxes and levies, gas D2 [R]: 2019-S1 0.0438; 2022-S2 0.1266; 2024-S1 0.0660; 2026-S1 0.0696; D1 2026-S1 0.0903; D3 2026-S1 0.0581. The full tax-exclusive series can be fetched with the URL above and `tax=X_TAX`. The API returned a single "all bands" gas value only for 2024-S1 (0.0812 incl. taxes, 0.0671 excl.) [R]. Which band a typical Jette dwelling falls in was not determined.

## Recent figures and scenarios
- **CREG** (regulator): average annual household bills of €1,170 (electricity) and €1,284 (gas) in "August" (year unclear in the summary); expected €1,295/yr for a new electricity contract in June 2026 for a Flemish household [S] (Brussels Times / Belga). The social gas tariff was raised 15% in Q3 2026 after higher gas prices Feb–May 2026; capped social gas tariff max 5.458 c€/kWh incl. VAT [S] https://www.brusselstimes.com/2199054/energy-regulator-announces-15-hike-in-the-social-rate-for-natural-gas. CREG primary pages not opened.
- **EU ETS2 (building heating carbon price, from 2027):** a Federal Planning Bureau impact analysis estimates +€250 to +€400 per household per year in Belgium, gas about +16% and fuel oil about +21%, assuming full pass-through at €60/tonne [S] https://www.brusselstimes.com/1655862/eu-carbon-tax-to-cost-belgian-households-e250-400-per-year. FPB original not opened (plan.be). Highly relevant to the gas price path in the retrofit NPV.
- **FPB electricity scenarios:** three scenarios for climate-neutral electricity by 2050; generation cost expected to rise from 2030 and not return to pre-transition levels [S] https://www.brusselstimes.com/1762226/cheap-or-dependant-belgium-faces-stark-energy-choices-before-2050.
- **Residential price path (€/kWh by year) to 2040/2050 for gas or electricity: not found.** Candidates, not opened: FPB energy outlook, Belgian NECP scenarios, EU Reference Scenario.
- The Eurostat history supports a historical volatility range only; the forward path is an assumption for the economists.
