# Tenure, buildings, co-ownership, rental metering

Tags: **[R]** read in the source; **[S]** from a search-result summary only. Statbel's website blocks automated fetching; its "bestat" PDF export endpoint was retrievable.

## Tenure

### Census 2021, Region level — **high (region), no Jette split**
- Share of dwellings occupied by their owner, Brussels Region: 38.00% (2011), **38.12% (2021)**; Belgium 65.58% → 64.53% [R]. Source: Statbel Census table https://bestat.statbel.fgov.be/bestat/api/views/26fb787d-614b-4ff3-bb26-71ce16d1fcf4/result/PDF
- Buildings with a single dwelling, Region: 16.90% (2011), **14.97% (2021)**; Belgium 69.69% → 66.09% [R]. Source: .../views/056102b4-5ec0-4ca7-88d6-5eb78f07d62c/result/PDF
- Number of dwellings, Region: 487,582 (2011) → **525,706 (2021)** [R]. .../views/4c1bc080-5e34-44fd-aab3-36e4eadfc9ac/result/PDF
- Dwellings built before 1919, Region: 30.47% (2011), 29.74% (2021); Belgium 22.99% → 21.28% [R]. .../views/67fe821f-c687-4c90-8692-f3c1330c5b92/result/PDF
- Owner-occupancy by type, Region: 76.9% of houses vs 31.6% of apartments (Statbel page, via search summary) [S] https://statbel.fgov.be/en/themes/census/housing/type-ownership.
- The bestat views above filter only to Region/province. A commune-level Census 2021 tenure table: **not found** (the Statbel site is bot-protected; ask Statbel or use Census open data).
- Licence: Statbel open data, free reuse [S]. Format: PDF/HTML export from bestat; CSV-style download via Statbel open data.

### Jette — Census **2011** only — **medium**
IBSA "Zoom sur Jette" 2024 [R], section 9.1: "la part de logements occupés par leur propriétaire est plus élevée à Jette (48 %) qu'à l'échelle de la Région (39 %)" — based on Census 2011. No Census 2021 Jette figure found. Because the Region moved 38.00% → 38.12% between 2011 and 2021, Jette is probably still near 48%, but that is an inference, not a source.
PDF: https://ibsa.brussels/sites/default/files/publication/documents/Jette_FR_cor.pdf

### Landlords, private vs social tenants
- Region: an undated UCLouvain document gives 43% owners, 57% tenants (46% private sector, 11% social) [S] (https://research.dial.uclouvain.be/bitstreams/2c7aed38-04c1-45cd-a63d-c0596da161d0/download); year unverified. Treat as low confidence.
- Social housing: Jette 1,406 social dwellings at 31 Dec 2020 = 6.3 per 100 households; Region 7.2 (IBSA Jette page and Zoom PDF) [R].
- Share of landlords among households, number of dwellings per landlord, small vs institutional landlords: **not found**. (Relevant for the rental-building phase; likely sources: SPF Finances cadastre/AGDP micro-data, Statbel "Owners of dwellings", BISA housing studies — none verified.)
- Belgium-wide, EU-SILC (Eurostat ilc_lvho02, API read 2026-11-06) [R]: owners 70.9%, tenants 29.1% of population in 2025; among people below the 60% poverty threshold 40.5% are owners and 59.5% tenants; above the threshold 74.6% / 25.4%. Query: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_lvho02?format=JSON&geo=BE. Belgium only, not Brussels.
- Rents: Jette average rent €743 vs €739 for the Region in 2018 (SLRB rent observatory, quoted in Zoom PDF) [R]. Newer commune rents: IBSA says none available at the time of writing.
- Apartment median sale price Jette €220,000 (2025) vs Region €270,000 [R] (IBSA Jette page).

## Buildings

### Residential building stock, Jette (Statbel & SPF Finances cadastre via IBSA) — **high**
[R] from the Zoom PDF, section 9:
- 1 Jan 2021: 7,510 buildings (6,654 residential, 856 non-residential) and 24,852 dwellings, of which 1,406 social. IBSA page: 25,007 dwellings in 2025 (24,764 in 2020).
- Residential buildings by type (cadastral nature), 2021: 2-façade houses 71%; 3-façade 5%; 4-façade 1.6%; apartment buildings 23%. Region: 64% / 9% / 4% / 23%.
- Age of residential buildings (Zoom chart 9·2, 1 Jan 2021), Jette, in the order Before 1900, 1900–18, 1919–45, 1946–61, 1962–70, 1971–91, 1992–2011, after 2011, unknown (as parsed from the PDF text): 11 / 13 / 36 / 20 / 8 / 5 / 6 / 1 / 0 %; Region 13 / 23 / 28 / 19 / 7 / 5 / 4 / 1 / 0 %. The PDF text said buildings after 1970 are 12% of Jette's residential stock. Check the chart visually before re-quoting the per-band numbers.
- Dwelling size (Census 2011): 4-room dwellings 31.5% of Jette dwellings, 5-room 19%, 3-room 15%.
- Units per building: derived by me, 24,852 dwellings / 6,654 residential buildings ≈ 3.7 dwellings per residential building (mixes houses with 1 unit and apartment buildings; distribution by size class: **not found**).

### Dwelling-level data for joining to the map
See `geodata.md` (UrbIS buildings, cadastre-derived attributes).

## Co-ownership (condominiums)
- Prevalence of co-ownership in Brussels or Jette (number of associations, share of dwellings): **not found**. A BCE-open-data-based count is the likely route (precedent: a 2019 Liège study counted co-ownership associations from BCE open data [S]), but registration is incomplete, so BCE counts undercount [S] (lexgo / La Libre articles in search results). A Bruxelles Environnement seminar deck (June 2026) at https://environnement.brussels/media/21498/download discusses the number of unregistered co-ownerships [S].
- Proxy: 23% of Jette's residential *buildings* are apartment buildings, but those hold many more dwellings than their share; the share of dwellings in apartments is not in the sources I could open. Region Census: 14.97% of buildings have one dwelling [R].
- BISA Focus 83 (13 July 2026) press release [R] https://bisa.brussels/sites/default/files/2026-07/PB_Focus83_lay.pdf: "slechts een derde van de woningen is door de eigenaar bewoond en eengezinswoningen vertegenwoordigen slechts 14 % van de woningen" (only a third of dwellings are owner-occupied, single-family houses are 14%); it attributes lower premium uptake in co-ownerships to collective decision-making. Note this "one third" differs from Census 38.12% — different definition/year; use the Census figure and cite BISA only for the qualitative point.

### Belgian co-ownership law: majorities for works (Civil Code Book 3, art. 3.88) — **confidence: medium**
I could not open the official text (Justel/Moniteur). The wording below was extracted from monacp.be's page on the Civil Code reform (a co-ownership practitioner site that reproduces the article) https://www.monacp.be/bienvenu/la-loi-sur-la-copropriete/reforme-du-code-civil/ — **verify against Justel before quoting to policymakers**.
- Art. 3.88 §1, 1° (two-thirds of votes): "de tous travaux affectant les parties communes" — works affecting common parts. Works imposed by law and conservatory or provisional-administration works can be decided by absolute majority instead. Also two-thirds for statute changes concerning only enjoyment, use or administration, and for the amount above which competitive tendering is mandatory.
- Art. 3.88 §1, 2° (four-fifths of votes): any other statute change including "la modification de la répartition des charges de copropriété"; change of destination of the building; reconstruction after partial destruction; acquisition or disposal of common real estate; division/merger of lots; total demolition and rebuilding.
- The page found no special energy-saving rule in 3.88 §1. Whether energy-retrofit works count as "imposed by law" (e.g. under Brussels PEB/Renolution rules) is **not established**; an amendment on defining works imposed by law was reported in the Chamber (search result from dekamer.be, 56K0849) [S] — status unknown.
- Quorum (Lexgo English summary, https://www.lexgo.be/en/papers/civil-law/property-law/new-belgian-property-co-ownership-law-explained,59061.html [R], describing the 2010 reform): valid deliberation needs "more than half of the co-owners which in turn must hold at least half of the shares in the common parts", or presence/representation of co-owners holding "more than three fourths of the shares". Check the current art. 3.87 §5 wording — Lexgo describes the pre-2021 regime.
- Practical reading for the model: whole-building envelope/roof/heating works need ≥2/3 of the votes (votes weighted by quotas) unless classed as imposed/conservatory; changing how the cost is split needs 4/5.

## Utilities in rentals (metering)
- Brussels rules summary (secondary): tenants usually open their own electricity and gas contracts via the EAN code of each meter; communal charges (lift, stair lighting, cleaning) are split by floor area or co-ownership shares; water and heating are billed by individual meters where possible, otherwise by a key stated in the lease; provisions are reconciled annually while flat-rate charges are not [S] (FAQ site seobailbelgique.pages.dev; VUB renting guide https://vub.be/sites/default/files/2025-04/Renting%20a%20property.pdf).
- Brussels excessive-rent rules list "no individual water and electricity meters" among major quality defects [S] (Brussels Times, https://www.brusselstimes.com/1540256/how-to-know-if-your-rent-is-excessive-in-brussels).
- Share of Brussels rental dwellings with shared (collective) heating / individual metering: **not found**. The Brussels Housing Code text and the Region's rent portal (loyers.brussels) should be the primary sources; not opened. This matters for the split-incentive modelling: the Renolution premium and PEB certificate data (see `retrofit-costs-savings.md`) are the only quantitative handles found.
- Rent indexation is linked to the EPC class in Brussels (PEB report mentions "changement de régime pour l'indexation des loyers" as a driver of certification) [R, PEB report 2025, p. 5 area]. Detailed rule: not read.
