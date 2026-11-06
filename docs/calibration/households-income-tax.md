# Households, income, income tax (Jette / Brussels)

Evidence tags: **[R]** = I read the figure in the source file/page itself. **[S]** = taken from a web-search result summary; the page itself was not opened (or was blocked), so verify before presenting. "Not found" = searched, no figure.

Access note: Statbel's own website (statbel.fgov.be, fin.belgium.be) served a bot-check page to my fetcher, so I could not read Statbel/FPS Finance pages directly. IBSA republishes the same Statbel fiscal tables as Excel files that I could download and read (see source 1).

## Sources

### 1. IBSA "Statistique fiscale des revenus" tables (Statbel data, commune level) — **confidence: high**
- Contents: Statbel personal-income-tax statistics, reproduced by IBSA/perspective.brussels for the 19 Brussels communes, the three Regions and Belgium. Includes: total net taxable income, number of returns, returns by income class (2023 only), mean and median income per inhabitant / per return, after-tax income, wealth index, total personal income tax and its components (state tax, communal surtax), and equivalised after-tax income by age class, household type, nationality and sex.
- Granularity: **commune (Jette is a row)**. Not statistical sector.
- Years: income years 2005–2023 for the totals; breakdowns by age/household type are income year 2023 only. File names carry publication dates (Dec 2025 and May 2026).
- Licence/access: IBSA page https://ibsa.brussels/themes/revenus-et-depenses-des-menages/statistique-fiscale-des-revenus [R]. Direct downloads (HTTP 200, retrieved 2026-11-06):
  - https://ibsa.brussels/sites/default/files/documents/2.1a_rev_dep_menages_stat_fisc_declarations_20251216.xlsx
  - https://ibsa.brussels/sites/default/files/documents/2.1b_rev_dep_menages_stat_fisc_menages_prives_20260526.xlsx
  - Licence: not stated on the page I read; Statbel's open-data terms (free reuse) are the underlying terms [S]. Cite "Statbel (DG Statistics) / IBSA".
- Format: XLSX, one sheet per table.
- Caveat: the unit is the tax return (a joint return counts once), not the household. Tax returns exclude people who file nothing. "Net taxable income" is after deductions.

**Jette values read from the files [R]** (income year 2023 unless stated; tables 2.1.x in the files):

| Indicator | Jette | Brussels Region | Belgium |
|---|---|---|---|
| Number of returns (2.1.1.2) | 29,535 | 662,954 | 6,846,186 |
| Total net taxable income, M€ (2.1.1.1) | 993.4 | 23,154.0 | 274,708.0 |
| Mean net taxable income per inhabitant, € (2.1.2.1) | 18,360 | 18,529 | 23,352 |
| Median net taxable income per return, € (2.1.2.6) | 25,677.56 | 24,487.83 | 30,099.86 |
| Median after-tax income per return, € (2.1.2.14) | 22,334.10 | 21,607.93 | 24,722.49 |
| Median equivalised after-tax income per inhabitant, € (2.1.5.1) | 19,746.04 | 19,328.54 | 24,575.83 |
| Total personal income tax, M€ (2.1.4.1) | 209.7 | 5,288.8 | 62,840.1 |

Jette's median taxable income per return was 23,196 (2021), 24,172 (2022), 25,677.56 (2023) [R]. IBSA's Jette page gives the "wealth index" (Belgium = 100) as 81 in 2018 and 79 in 2023, vs 78 and 79 for the Region [R] (https://ibsa.brussels/chiffres/chiffres-cles-par-commune/jette).

**Returns by income class, Jette, 2023 (table 2.1.1.3) [R]** — classes in € of total net taxable income: zero income 3,795; <10,000: 4,657; 10,000–20,000: 5,417; 20,000–30,000: 7,350; 30,000–40,000: 4,003; 40,000–50,000: 2,724; >50,000: 5,384. Total 29,535 (33,330 including zero-income returns, per the file's last column). (Column mapping checked by arithmetic: the six classes sum to 29,535 and adding the zero-income returns gives 33,330, matching the file's two total columns.)

**Median equivalised after-tax income, Jette, 2023, by age class (table 2.1.5.3) [R]**: 0–17: 15,936; 18–24: 16,488; 25–29: 20,615; 30–39: 20,283; 40–49: 19,432; 50–64: 22,335; 65+: 23,936; all 19,746.

**By household type, Jette, 2023 (table 2.1.5.5) [R]**: living alone 21,359; married no children 26,848; married with children 17,642; cohabiting no children 28,685; cohabiting with children 22,128; single-parent 15,898; other 19,908.

**Income tax paid, Jette (table 2.1.4.2) [R]**: state tax 197.06 M€ and communal surtax 12.66 M€ in 2023 (185.79 and 11.93 in 2022). Derived by me: 209.72 / 993.41 = 21.1% of total net taxable income went to personal income tax in Jette in 2023 (average rate, not marginal).

### 2. Statbel open data "Fiscal statistics on income" by **statistical sector** — **confidence: medium (not opened)**
- A Statbel wiki entry titled "Fiscal statistics on income by Statistical sector", period 2005–2023, and an ODWB mirror "statbel-revenus-par-secteur-statistique" appear in search results [S]. Statbel open-data page: https://statbel.fgov.be/en/open-data (the specific dataset page https://statbel.fgov.be/nl/open-data/fiscale-statistiek-van-de-inkomsten is listed in search results). Statbel states open data may be reused free of charge, commercial or not [S].
- I could not open the dataset page (bot check) so variables and file format are **not verified**. Sector boundaries are published at https://statbel.fgov.be/en/open-data/statistical-sectors-2025 [S].
- Why it matters: this is the only route to a within-Jette income map. Action for the team: download in a normal browser and check the variables (mean/median income per sector, deciles if present).
- Third-party: Geolocet sells a derived sector income dataset — not recommended (non-official).

### 3. Tax-by-decile — **not found**
No source I could open gives tax payable by income decile for Jette or Brussels. The class table above (returns by income class) plus the federal rate schedule below allow a rough construction of a tax schedule, but a decile table needs microdata (Statbel/FPS Finance request or the Federal Planning Bureau's MODTRIM / SILC-based models; none verified).

### 4. Marginal tax structure — **confidence: medium (secondary sources)**
- The official page https://fin.belgium.be/en/private-individuals/tax-return/income/tax-rates could not be opened (bot check). Search-result text from it says rates run 25%–50% and the personal tax-free allowance is €10,910 (income year 2025) and €11,180 (income year 2026) [S].
- Income year 2025 brackets reported consistently by several secondary sources (Dexxter and others, via search): 25% up to €16,320; 40% up to €28,800; 45% up to €49,840; 50% above [S]. For income year 2026 the secondary sources disagreed (one gives 25% to €16,720, 40% to €29,510, 45% to €51,070, 50% above) [S] — **do not use without checking the official table**.
- Local surtax: communal surtax is an extra percentage on the state tax. Jette's 2023 communal tax of 12.66 M€ against 197.06 M€ state tax implies about 6.4% (my arithmetic on [R] values); the statutory Jette rate was not located.
- Relevance to a deduction/credit: a deduction's value is worth the marginal rate (25–50%), a credit is rate-independent but only usable up to tax payable. Note that 3,795 + 4,657 = 8,452 of 33,330 Jette returns (25%) have zero or <€10,000 taxable income [R] — for them a deduction or non-refundable credit is worth little or nothing. Whether the federal tax-reduction regime for energy-saving works is in force in Brussels in 2026: **not found**.

### 5. Household composition and age (Jette) — **confidence: high**
IBSA Jette key figures page [R] https://ibsa.brussels/chiffres/chiffres-cles-par-commune/jette (sources: IBSA & Statbel, National Register):
- Population 52,854 (1 Jan 2021) → 54,330 (1 Jan 2026). Region: 1,219,970 → 1,255,834.
- Private households: 22,273 (2021) → 22,672 (2026); average size 2.3 → 2.4 (Region 2.2 → 2.1).
- Single-person households 38.9% (2026) (Region 46.8%); single-parent households 14.2% (Region 11.7%).
- Age 2026: under 18: 23.0%; 18–64: 62.2%; 65+: 14.8%. Average age 38.6.
- Foreign nationality 26.4% (Region 36.7%).
- IBSA "Zoom sur Jette" 2024 (PDF, 10 MB): https://ibsa.brussels/sites/default/files/publication/documents/Jette_FR_cor.pdf [R] — says Jette's median income is "à peine supérieur" to the regional one, Gini inequality is moderate vs the Region, and very low and very high incomes are less present than in the Region. It also notes Jette is attracting better-off young households and that some neighbourhoods may gentrify.
- Census 2021 (Statbel) regional: 559,260 private households in the Region, average size 2.16 [R, via bestat PDFs https://bestat.statbel.fgov.be/bestat/api/views/df0f5758-8ba7-4e05-966e-cf01a4930ff9/result/PDF and .../d2eda94d-42f1-4749-9397-d1033628f798/result/PDF].

## What is still missing for the model
- Income by statistical sector (source 2 not verified) and any decile table.
- Wealth/savings of households (liquidity for the up-front share of retrofit). Not found at commune level; EU-SILC (Eurostat) has Belgium-level indicators only. HFCS (ECB) is the standard source — not searched.
- Joint tax-return handling: the unit is the return; a household-level link to tenure/dwelling is not available in public data.
