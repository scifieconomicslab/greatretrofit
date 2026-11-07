# Great Retrofit on the Jette scene: integration check (2026-11-06)

First end-to-end run of the pack with the real scene in a real browser. **No economic result is claimed or implied anywhere here**: every model number is a placeholder (v3/docs/placeholders.md). The state counts below are quoted only to show the page runs.

## Setup

| | |
|---|---|
| Scene | whole commune of Jette, `jette-commune-scene.json` from the paperdolls ingest (OSM relation 58258, planet state 2026-11-06): 9,214 buildings, 1,320 roads, 8,705 trees. Copied from the shared notes folder into `cache/` (gitignored); `scripts/build_jette_demo.sh` regenerates it from Overpass when it is missing (not run here: the cached scene was reused, so the fetch path of the script is untested). |
| paperdolls | `main` at 603408a (pack shell, worker runtime, picking, inspector). Read only. |
| Build | `scripts/build_jette_demo.sh` -> `build/jette_retrofit.html`, 4.8 MB, 0.4 s |
| Browsers | (a) the built-in browser pane (800x600 screenshots of a 1024x768 CSS viewport, devicePixelRatio 2), served from `python -m http.server` because the pane refused `file://`; (b) headless Chromium 1243 over DevTools (`scripts/verify_jette_browser.mjs`), `file://`, 1440x900, run at DPR 1 and DPR 2. Software rendering in both (no GPU). |

## What works (verified)

- `paperdolls pack check` passes on `packs/great-retrofit` and on the bundled `dist/` (6 warnings, all "planned component" notices for charts, KPIs and the segments channel).
- Page loads with **no console messages and no exceptions**, **one request in total** (the file itself) plus the worker blob. No other network request in either browser. Load to first frame: 3.5 s (DPR 1), 4.6 s (DPR 2), headless.
- **Binding**: banner says "8105 of 8105 placed", `binding.warnings` is empty. Checked in the page against the scene: all 8,105 model buildings stand on scene buildings classed `residential` (433) or `probable` (7,672); none on `other` (1,109 excluded); the entity-to-scene index and its inverse agree for all 8,105. 22,986 dwelling units in total (1 to 135 per building). Tenure split from the placeholder rules: 2,573 owner-occupied, 3,643 condo, 1,889 rental ("not modelled yet", shown grey). Sample rows: scene building w30129320 (78 m2, 2 storeys) -> 2 units; w31142391 (976 m2, 4 storeys) -> 39 units.
- **Run**: worker runtime (`controller.mode == "worker"`); a full 180-month rerun with 8,105 buildings takes about 0.9 s (`lastRunMs`), on a slider release the run is replaced and time is kept.
- **Sliders**: dragging "Rebate rate" from 0.3 to 0.85 changed the run (`runs` 1 -> 2, params updated); frame time while dragging was unaffected (below). `store.resetParams()` returns to defaults; preset "Public retrofit service" gives a different trajectory (month 60: not_retrofitted 3121, partial 1909, retrofitted 1186, not_modelled 1889; for the same month under defaults the page showed 3352 / 1984 / 880 / 1889). Presented only as "the controls change the run".
- **Play / pause / timeline / speed**: play advanced 120 months in 5 s at 24 months per second; pause stops; the timeline slider and `setTime` scrub. Month label and the bottom readout follow.
- **Colouring and legend**: wall colours follow the manifest (tan not retrofitted, amber partial, green all, grey rental); the scaffold overlay shows on partial buildings; the four "Colour walls by" options are listed; legend entries match `pack.yaml` colours and labels.
- **Picking and inspector**: hover shows "Building 1867: state Some units retrofitted"; click selects (three different buildings selected in the scripted run); inspector lists state, tenure, adopted_share, units, income_q_mean; Escape clears the selection.
- **Narrow viewport**: 390 px and 768 px: no horizontal overflow (`scrollWidth == clientWidth`); controls stack above the map.

## Frame time

Gap between `requestAnimationFrame` callbacks, headless Chromium, software rendering, 9,214 scene buildings (8,105 bound). Run-to-run noise is large (two DPR-1 runs differ by 2x in the near-zoom rows), so read these as ranges. Vsync is 16.7 ms.

| | far zoom (Fit) | near zoom (street level, about 150 buildings in view) |
|---|---|---|
| idle | 16.7 ms median; first-paint stall of 0.4 to 0.6 s while the far layer is first painted | 16.6 to 36 ms mean |
| playing 24 months/s | 27 to 34 ms mean, p95 50 ms | 31 to 45 ms mean, p95 50 ms |
| dragging a slider | 17 to 18 ms mean, p95 33 ms | 18 to 42 ms mean, p95 33 to 50 ms |

All of these are 20 to 60 fps. **In the built-in browser pane the same page ran at 1 to 3 fps (gaps of 0.4 to 1.0 s)**, but there a trivial test (blitting one 1776x2220 canvas and drawing a rectangle every frame, no paperdolls code) also gave 560 to 600 ms per frame, and the page's own animation callbacks cost only 14 to 29 ms. The pane's compositor is the bottleneck at DPR 2, not this pack; I could not measure the page on a GPU-backed browser.

## Bugs and observations

Severity: **High** blocks the demo's purpose, **Med** misleads or hampers a policymaker, **Low** polish. "Owner" is the repo that should change.

| # | Sev | What | Repro | Owner | State |
|---|---|---|---|---|---|
| 1 | High | The pack never bound to the scene: its runtime had no `bindScene` hook and `bind.js` returned another shape (`entities.building.specs`, `sceneIds`, a `Map`) than the shell takes (`{entities: {building: {count, attrs}}, sceneIndex: {building: ids}}`). The shell would have drawn model buildings in its invented order, which says nothing about where anything is. | Build `packs/great-retrofit` and open with a scene: no "placed" line, `labPack.binding.bound == false`. | this repo (`bind.js`, glue) | **Fixed**: new `hook.js` wraps `PaperDolls.registerRuntime` for this id (before `runtime.js` loads, so `runtime.js` is untouched), adds `bindScene` and makes `init` read `attrs.specs`. `tools/bundle.js` includes it. Test added (`test_bind.js`). |
| 2 | High | `bind.js` read `residential` only as a boolean, but the paperdolls ingest writes the strings `residential`, `probable`, `other`. Every building fell into the "older format" guess from `osm.building`, so the scene's own classification (outbuildings under 30 m2, shops, schools) was ignored and counted as an assumption. | Run `bindScene` on `cache/jette-commune-scene.json` before the fix. | this repo (`bind.js`) | **Fixed**: strings map to true/false; `probable` is included and counted in `report.assumed.residential` (7,672 of 8,105). Test added. |
| 3 | Med | The pack built from the folder `packs/great-retrofit` (the documented command in the task, and what `pack build` is given by default) inlines only `runtime.js`; the build succeeds but without `prng.js`, `hook.js` and `bind.js`. The working build is from the generated `dist/`. I did not open the folder build in a browser. | `pack build packs/great-retrofit --scene ...` | this repo (workflow) / paperdolls (could inline more than `runtime.entry`) | Worked around: `scripts/build_jette_demo.sh` bundles first. `from: scene` added to the manifest (it was missing, spec asks for it). |
| 4 | Med | **State colour is hard to see at far and mid zoom.** Walls carry the colour; at the default isometric view roofs (dark slate) cover most of the picture, so the commune looks near black at "Fit" and the retrofit state shows only on street-facing walls. The picture a policymaker first sees does not show adoption. | Open the page, press Play, watch the far view (`01_far_start.jpg`, `02_far_playing.jpg`). | paperdolls (renderer: roof/wall treatment, or a roof tint channel) | Open. |
| 5 | Med | **No charts or KPIs are drawn**: `chart`/`kpis` components are planned (P5). The bottom area is a raw text dump of every series with unrounded floats and `NaN` for no-data ("q1 NaN", "price NaN", "0.007942579075427"). | Look at the bottom strip at any size. | paperdolls (readout formatting, P5 charts). The `NaN` rows come from series that have no value at month 0 (frames from `runtime.js`, `v3-mechanics`). | Open. |
| 6 | Med | **The inspector is not visible without scrolling the right column** (it sits below the legend and Display switches; at 1440x900 and in the 1024x768 pane it is off screen). A click selects, but nothing visible happens unless the user scrolls. | Click a building; right column; see `06_selected_inspector.jpg` (only the tooltip and the map are visible). | paperdolls (layout) | Open. |
| 7 | Low | Inspector and tooltip name the building by model index ("Building 1867"), not the OSM id (`w30129320`), and show nothing about the real building (area, storeys, **storeys assumed** for 98.8% of Jette). The OSM id and footprint area are available in the scene. | Click any building. | paperdolls (inspector could show scene fields) and this repo (could pass `attrs`) | Open. |
| 8 | Low | The legend lists every wall scale at once (Retrofit state, Units retrofitted, Ownership type, Mean income) whichever one is active, so it does not say which colouring is on screen. | Legend at the right. | paperdolls | Open. |
| 9 | Low | At 390 px the map is a 240 px strip below a long list of controls; the user has to scroll past all sliders to see the map. Works, but is poor on a phone. | `09_narrow_390.jpg`, `10_tablet_768.jpg` | paperdolls (layout) | Open. |
| 10 | Low | First paint at far zoom stalls for 0.4 to 0.6 s (far layer is painted in 6 ms slices, then swapped in). Playback at far zoom is 30 to 50 ms per frame; each month's new colouring triggers a layer repaint, so the far view updates in steps. | Reload; measure `idle` at far zoom. | paperdolls | Open (known; see their far-zoom notes). |
| 11 | Info | Placeholder rules give 45% of buildings the condo tenure (3,643 of 8,105) and 23% rental (not modelled). This is the pack's placeholder assignment, not data. | `labPack.store.frame().entities.building.tenure` | this repo (`runtime.js` / `bind.js` rules); `runtime.js` is `v3-mechanics`' | Report only. |

## What I changed in this repo

- `packs/great-retrofit/hook.js` (new), `tools/bundle.js` (include it), `bind.js` (class strings), `pack.yaml` (`from: scene`), `tests/test_bind.js` (two tests).
- `scripts/build_jette_demo.sh`: builds from a clean checkout (fetch + ingest only if no cached scene; bundle; check; build). `scripts/verify_jette_browser.mjs`: the headless run used above, rerunnable. `.gitignore`: `cache/`, `build/`, `packs/great-retrofit/dist/`.
- `docs/verification/`: 10 screenshots (jpg, 1.8 MB total) and the two JSON run logs.
- Tests: `pytest packs/great-retrofit/tests` 21 passed; `node tests/test_bind.js` and `test_parity.js` pass.
- Not touched: paperdolls, `packs/great-retrofit/runtime.js`.

## Could not verify

- Frame rate on a GPU-backed browser, or on a real machine's display; the pane and headless runs are software-rendered. Numbers above are a floor and noisy.
- The Overpass fetch branch of `build_jette_demo.sh` (the scene was copied, not fetched, to stay polite to the service). `file://` loading was checked in headless Chromium only; the pane refused `file://`.
- The unbundled folder build in a browser (bug 3).
- Colouring by the other three wall options was listed and the legend checked, but I did not inspect each option's picture.
- The "Display" switches (people, vehicles, ink outline, pixel, fog) were not exercised.
- Touch input, and screen readers.
- Anything about economic meaning: nothing was assessed, by design.

## Addendum (2026-11-06): dashboard, channels, tenure preset

Pack rebuilt against paperdolls `main` at f23f9d4 (P5 charts/KPIs/compare, P6 channels, P7 terrain), Jette scene as above (8,105 of 8,105 placed, no binding warnings), headless Chromium 1440x1500, `file://`, software rendering. Script: `node scripts/verify_jette_dashboard.mjs` (pictures in `docs/verification/dashboard/`, `d01` to `d11`). **No economic result is claimed.** Every number visible in those pictures is a placeholder; I looked at whether things draw, not at what they say. Note that the presets are not matched on public cost (see item B), so no comparison in the pictures is like for like.

### What was checked and works

- Page loads with no console messages or exceptions and no network request other than the file itself (`network_non_file` empty).
- Dashboard: line chart (adoption by income quintile), three bar charts (public transfer per euro of price, share able to pay now, price per retrofit split into base cost and margin or overhead), three KPI tiles (public cost, bills saved, share of buildings treated as rental). Charts follow the timeline cursor; the bars move with the time shown (`d02` at month 60, `d03` at 120).
- A/B compare: switch, B chosen from the preset list, dashed B on every chart, "B ... vs A" lines under the tiles with the arrow and sign (`d08` rebate-only vs pay direct, `d09` rebate-only vs public service, `d10` map showing B). No NaN in the page text with compare on.
- Channels on the whole commune: `outline` (red box, "cannot pay now"; visible at street zoom and at Fit, `d04`, `d07`), `insulation` overlay on all-retrofitted buildings (green cladding, `d06`, `d07`), `segments` and wall colour on a part-retrofitted building (olive wall at the right edge of `d07`), `groundtint` (pale tiles under the commune, legend "mean over a 250 m grid").
- Tenure alternative: preset "More rental buildings (grey, not modelled)" turns 41% of buildings grey (3,339 of 8,105 against 1,889 by default); the KPI tile and the banner say so (`d11`).
- No-data: at month 0 the charts and tiles draw no value for series that have none yet (`NaN` in the pack frame is the spec's no-data value). The only place `NaN` reaches the page is the text readout (item A).

### Looks wrong or is missing, and who owns it

| # | Sev | What | Owner |
|---|---|---|---|
| A | Med | The text readout above the tiles (`packhost.js:402`) still prints every series raw: unrounded floats ("0.0008699434536755111") and the word `NaN` at month 0 ("base_cost NaN"). The charts and tiles beside it format and handle no-data correctly, so this strip is now redundant noise. Nothing to fix in the pack: the runtime sends what the spec declares (`NaN`), tested by `tests/test_nodata.*`. | paperdolls (readout formatting; or let a pack hide series from it) |
| B | High for the story | The presenter story compares delivery modes "at equal public cost". The model has no budget-matching: the three presets differ a lot in public cost (month 120, placeholder values: about 48 M euros for rebate-only, 203 M for public service in the pictures). A fair comparison needs a public-budget cap or a solver that sets the rebate rate for a given cost. Not invented here. | this repo (model, needs an economist's decision on what is held equal) |
| C | Med | No way to set the default B in the manifest: the panel opens with B unset and the presenter picks the preset by hand. Presets are named so the two pairs (rebate only vs pay direct, rebate only vs public service) are one click each. | paperdolls (manifest key for a default compare pair) |
| D | Med | Layout: the map is a short strip above a tall dashboard in the bottom region (about 320 px of a 1000 px viewport at Fit); the charts push the map up. Charts in the right column would compete with the legend instead. A `pd-layout` change is in flight, so I left the arrangement simple. | paperdolls (`pd-layout`) |
| E | Low | `entities.building.fields.units` triggers "declared but no mapping or component shows it" although `segments` uses it as `total`. | paperdolls (validator) |
| F | Low | `outline` is drawn on many buildings at Fit and the commune reads red at far zoom (`d02`), which hides the wall colour. It follows the placeholder finances, not a finding, but a presenter may want it only near zoom. | paperdolls (far-zoom treatment of outlines) |
| G | Low | Segments are hard to tell from a wall colour mix at the zoom used; I did not isolate a building with 2 of 6 units done. | not checked |
| H | Info | `pack check packs/great-retrofit` on the folder fails the runtime-load check ("RetrofitPRNG must be loaded first") because `prng.js` and `hook.js` are not inlined; `scripts/build_jette_demo.sh` checks and builds the bundled `dist/` and keeps a TODO for `runtime.files`. The validator on main does not accept `runtime.files`, so it is not in the manifest. | paperdolls (`runtime.files`, `pd-layout`) |
| I | Info | The tenure rule is placeholder; condo 45%, rental 23% are its outcome, not data. Candidate real figures are in `v3/docs/placeholders.md` ("Tenure rule") with their confidence; none is used. | this repo (calibration) |

### Model changes behind this (this repo)

- New frame fields: building `units_cannot_front` (int), series `tenure_counts`; pack-only derived fields `units_done`, `cannot_front`; pack series `buildings_by_tenure`, `rental_share`. Documented in `v3/docs/frame-schema.md`.
- New run parameters `rental_share_single`, `rental_share_multi` (placeholders, defaults equal to the scene rules, so nothing changes unless they move), in `v3/docs/placeholders.md`. Two new parity cases (`rental_share_override_s18`, `rental_share_zero_s19`); golden files regenerated, and a check that no previous value in any golden changed.
- No-data test (`tests/test_nodata.js`, `.py`): `null` in v3 frames and `NaN` in pack frames only in the five series the schema marks nullable, and equal to each other; entity arrays never hold NaN.
- Not run: DPR 2, the Overpass fetch branch of the build script, touch input, a GPU-backed browser.

> Update 2026-11-07: bug 3 and item H are closed. `pack check` and `pack build` work on `packs/great-retrofit` directly (`runtime.files` in `pack.yaml`, pack-local `prng.js`); `tools/bundle.js` and `dist/` are removed. See `merged-build-gaps.md`.
