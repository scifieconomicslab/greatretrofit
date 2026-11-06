# Calibration data survey — Jette / Brussels

Survey of public data that can fill the Great Retrofit model's parameters and improve the Jette map. Compiled 2026-11-06. This is a survey, not modelling; no code was changed.

## Reading the evidence tags
- **[R]** = I read the figure in the source file, page, API or PDF itself.
- **[S]** = taken from a web-search result summary; the page was not opened (or was blocked) — verify before showing to policymakers.
- "Not found" = searched without result. Nothing here comes from memory.
- Environment limits: statbel.fgov.be and fin.belgium.be showed a bot-check page to my fetcher and I did not try to bypass it. Where IBSA republishes Statbel tables, I used IBSA's Excel files. The Eurostat API and datastore.brussels downloads worked.

## Index
| File | Topic |
|---|---|
| [households-income-tax.md](households-income-tax.md) | Income, income tax, household composition, marginal tax structure |
| [tenure-and-buildings.md](tenure-and-buildings.md) | Owners/tenants, building types and age, co-ownership law, rental metering |
| [retrofit-costs-savings.md](retrofit-costs-savings.md) | EPC data, cost and savings evidence, Brussels support schemes, one-stop-shop precedents |
| [time-use-working-hours.md](time-use-working-hours.md) | Time use, hours, credit |
| [energy-prices.md](energy-prices.md) | Eurostat gas and electricity price series, scenarios |
| [geodata.md](geodata.md) | Building heights, terrain, OSM join, recommendations |

## Summary table
| Need | Best source found | Granularity | Year | Licence / access | Confidence |
|---|---|---|---|---|---|
| Income, tax paid | IBSA/Statbel fiscal tables (xlsx) | Jette commune | income yr 2023 | Free download from ibsa.brussels | High |
| Income by sector | Statbel fiscal stats by statistical sector | Statistical sector | to 2023 | Statbel open data (not opened) | Medium |
| Household composition, age | IBSA Jette key figures | Jette | 2021–2026 | Free | High |
| Marginal tax rates | Secondary sources only | Federal | 2025/26 | fin.belgium.be (blocked) | Medium |
| Owner / tenant share | Statbel Census 2021 (Region 38.12% owner-occupied); Jette 48% from Census 2011 | Region; Jette (2011 only) | 2021 / 2011 | Free | High (Region), Medium (Jette) |
| Building type, age | IBSA Zoom Jette (Statbel/cadastre) | Jette | 2021 | Free PDF | High |
| Co-ownership prevalence | — | — | — | — | Not found |
| Co-ownership voting rules | Civil Code art. 3.88 via monacp.be | Federal | in force since 2021 | Official text not opened | Medium |
| EPC / PEB stats | Bruxelles Environnement report | Jette (class shares), Region | to 01/2026 | PDF, free | High (but not representative of stock) |
| Retrofit cost per m² | — (only €30–40k per condo unit, INNOVATE 2020) | Region programme estimate | 2020 | Free PDF | Low |
| Modelled savings by measure | EPC report top-3 recommendations | Region | to 2025 | Free PDF | Medium (modelled, not measured) |
| Renolution premium rules | Official 2024 table; 2025–26 status | Region | 2024 / 2026 | renolution.brussels | High (2024 table), Low (2026 rules) |
| Public service precedent | Homegrade one-stop shop; Energiesprong | Region / abroad | 2018–2026 | — | Medium (design), Low (costs) |
| Hours/leisure by income | — | — | — | — | Not found |
| Mortgage / renovation loan terms | NBB via ING; ECORENO 2.5–3.5% | Belgium / Region | 2026 | — | Medium / Low |
| Energy prices | Eurostat nrg_pc_202/204 | Belgium | 2019–2026-S1 | Eurostat API | High |
| Energy price scenarios | ETS2 impact, FPB electricity scenarios | Belgium | 2027+ | News summaries | Low |
| Building heights | UrbIS 3D Constructions (LoD2) | Per building | monthly, 2026-10 | CC0 label, ambiguous; free download | High |
| Terrain | Brussels LiDAR 2021 (67 pts/m²); UrbIS DTM | Region | 2021 | CC BY 4.0 / CC0 label | High (LiDAR) |

## Findings worth knowing before modelling
1. **Jette income is close to the regional average but well below Belgium**: median net taxable income per return €25,678 vs Region €24,488 vs Belgium €30,100 (2023) [R]. A quarter of Jette returns (8,452 of 33,330) show zero or under €10,000 taxable income [R], so a tax deduction has little value for them.
2. **Owner-occupation is low at the Region level (38.12%, Census 2021) but higher in Jette (48%, Census 2011)** [R]. Most of the stock is pre-1946 and runs at 330–360 kWh/m²/yr in EPC averages [R].
3. **Renolution was a post-works reimbursement**, took more than a year to pay in the 2024 backlog, ended 31 Dec 2024, and its 2025–26 successor is undefined; an interest-free loan is planned [R]. Take-up skewed to owner-occupied houses in affluent south-east neighbourhoods [R, BISA Focus 83].
4. **Co-owners need two-thirds of votes for works on common parts**, four-fifths to change charge sharing (art. 3.88, via secondary quote) [R-secondary].
5. **Heights and terrain are obtainable for free and joinable to OSM** (UrbIS `inspire_Id` ↔ OSM `ref:databrussels`); see geodata.md.

## Top gaps the economists must fill
Parameters the sources could not supply (with what the model is left with):
1. **Retrofit cost per m² and per dwelling by type** (house / apartment / condo unit) and its range; only a €30–40k per-condo-unit programme estimate and non-Brussels ranges exist. Request anonymised Renolution invoice data.
2. **Realised (measured) energy savings and rebound** versus EPC-modelled savings; EPC averages are partly default-driven and the sample is not representative.
3. **Forward energy price path** for gas and electricity (and ETS2 pass-through); only history and a news-reported ETS2 impact exist.
4. **Discount rates / time preference and liquidity constraints** of households: no source on savings, wealth, or credit refusal by income; loan terms are partly unverified.
5. **Tax deduction value by income decile**: only the federal rate schedule (secondary) and the income-class counts exist; no decile table; whether any Brussels energy-works deduction exists is unresolved.
6. **Current premium/loan rules for 2026+** and the official income categories and caps.
7. **Co-ownership prevalence and dwellings-per-building distribution** for Jette; unit counts per building for the condo and rental phases.
8. **Landlord structure and split-incentive parameters**: share of tenants paying their own energy, collective heating share, pass-through of retrofit costs to rent.
9. **Take-up elasticity** to subsidy level and to hassle/time cost; no causal evidence found (BISA documents only the unequal distribution).
10. **Hours worked and leisure by income** (the model's time-cost mechanism): no Belgian table by income; only Eurostat hours by employment status.
11. **Public retrofit service unit cost and delivery capacity**: Homegrade is a coaching service; no cost per completed retrofit found.
12. **Jette tenure from Census 2021** and income by statistical sector (a quick manual download from Statbel).
