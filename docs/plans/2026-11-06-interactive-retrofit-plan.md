# Plan (rev. 2): interactive Great Retrofit for policymakers, drawn on Jette

Date: 2026-11-06. Status: draft. Revision 2 adds a paperdolls upgrade workstream and a per-model UI architecture ("model packs").

The list of open questions for the economists is kept separately and is not part of this repository.

## 1. What we are building

A page where a policymaker moves sliders (rebate rate and lag, credit access, delivery mode, vendor margin versus public overhead, energy price) and watches a map of Jette, Brussels respond. Buildings change state over simulated years, condos show how many units have retrofitted, and a side panel shows who gained and who was left behind.

**Driving policy question:** why do tax rebates on retrofits work poorly, and why are they regressive?

Three deliverables, in dependency order:

1. **v3 model** — the economists' dynamics (adoption and collective decision), in Python, tested.
2. **paperdolls upgrade** — turn the viewer from "play back a recording" into a live, interactive host that any model can plug into, with real geometry.
3. **Model pack for the Great Retrofit** — a declarative UI definition plus model code that plugs into that host.

## 2. Where we are now

| Piece | State | Gap |
|---|---|---|
| `v2` model | Weekly agent-based market for retrofit work (queues, banks, defaults) | Wrong mechanism for this question: no retrofit-or-not decision, no multi-household buildings. Known issues: wealth drains to zero, "finished" count ambiguous. |
| paperdolls model interface | Python `Params` + `run_simulation(params, on_week)`; hook is read-only and sees `(t, buildings, households, coops)`; states are four fixed codes | Fixed to four states and a coop-shaped world. Hook yields numbers per building only. No units inside a building. |
| paperdolls replay | `paperdolls export` records a trajectory to `.npz`; `replay.js` plays it with a scrubber; legend generated from `replay.mapping` (channels: `wall`, `overlay`) | Read-only. Nothing can change a parameter. Re-running needs Python and a rebuild of the page. |
| paperdolls placement | Model building *k* goes on scene building ranked *k* by distance from centre (invented) | Known issue 12. We need model-from-scene instead. |
| paperdolls ingest | One live run on a Jette bounding box: 2,162 buildings, 28% fit an asset, storeys mostly assumed | Whole-commune run, relations, elevation untested. |
| paperdolls UI | `viewer.html` has a hard-coded set of checkboxes (detail, ink, fog, pixel) and a replay scrubber | No way for a model to declare its own controls or panels. |

The viewer's JS engine (`vizlib.js`, `assetlib.js`, `buildinglib.js`, `replay.js`) is dependency-free and offline-capable, which is the right base. The work is in what sits around it.

## 3. Key decisions

**D1. New `v3` model package; v2 stays frozen as the queueing-financial reference.** The new mechanism is small and must be explainable in a minute. v2 financial modules (banks, co-ops) can be borrowed later if the economists want richer credit.

**D2. Models run live in the browser.** Python is the reference implementation; a JavaScript implementation runs in the page. A shared seeded PRNG and golden-trajectory tests prove they agree. Pyodide (Python in the browser) is the fallback if parity costs too much, and a small local server (HTTP/WebSocket) is a third runtime kept for heavy batch runs. The host treats all three through one *runtime adapter* interface (§5.3) so the choice is swappable per model.

**D3. Model-from-scene, not scene-from-model.** The scene (real Jette) is the source of buildings, floor areas, storeys and adjacency. The model pack turns that into model entities. Households remain synthetic and the page says so.

**D4. A general "model pack" architecture in paperdolls**, not a Great-Retrofit-specific page. A pack declares parameters, controls, charts, visual mappings, inspector content and a runtime. paperdolls provides the shell, the renderer and a registry of UI components. Escape hatch: a pack can register a custom component.

**D5. Time step:** monthly for v3, about 15 simulated years. Fast enough to re-run on every slider release.

## 4. v3 model (summary; full spec after economists' answers)

Revised after the first economist reply: the model is **economic, not social**. Households act when the money works over a time frame; there is no ideology premium and no solidarity lever (both parked, pending the economists' answers).

**Agents.**
- *Household:* income, tax payable, liquid savings, age and expected years in dwelling, weekly time budget (working hours), credit access.
- *Building:* tenure type, floor area, units, retrofit cost, annual energy saving, who pays utilities, energy class before and after.
- *Landlord* (second version): owns a rental building, decides on the building, may or may not pay utilities.
- *Lender:* one bank. Approves or refuses, at a fixed or household-dependent rate.
- *Delivery channel:* market vendor (margin), or public service (overhead, capacity). See the delivery modes below.

**Three ownership types.**

| Type | Decision | Included in |
|---|---|---|
| Owner-occupied home | Household decides alone | v1 of the model |
| Condo unit | Each owner decides for their unit; shared parts (windows, facade, roof) need a vote or permission; a neighbour's retrofit raises the chance of following | v1 |
| Rental building | Landlord decides. Incentive depends on who pays utilities: landlord pays means direct gain; flats metered separately means only a rent effect | v2, once the economists confirm the rent-effect treatment |

Owner-occupied homes are essential even if few: that is where the regressive pattern shows up.

**Household rule (all types).** Retrofit if NPV over the household's horizon is positive **and** the cost can be financed: from savings, or credit if access is granted.
`NPV = Σ discounted energy savings + net rebate - upfront cost - financing cost`
Delivery mode changes which terms appear:
- *Rebate (a):* upfront cost + loan; `net rebate = deduction_rate × cost`, capped by tax payable and arriving after a lag. The credit-access and tax-capacity terms are the regressivity channel.
- *Pass-through (b):* no upfront cost and no credit; government pays the vendor.
- *Public service (c):* as (b), with cost = labour + overhead and no profit; capacity-limited.

**Condo rule.** Each owner decides for their unit. A neighbour's retrofit raises the chance of following (parameter, channel to be confirmed). Shared-part measures need approval at a voting threshold (parameter; default the legal rule once checked) and costs are split by floor area (default).

**Canvassing as a time budget.** Each household has a time budget set by working hours. Canvassing spends it, so leisure-poor households (low-income with long hours, and high-income professionals) canvass less. Canvassing raises the chance a neighbour follows or a shared measure passes. Brussels time-use data feeds the budget distribution.

**Levers (sliders).** Deduction rate; refundable-credit toggle; rebate lag; credit access rule and rate; delivery mode (a, b, c) with vendor margin, public overhead and public capacity; means-test toggle; energy price scenario.

**Outputs (the five views).** (1) household cash timeline; (2) rebate per euro of cost by income quintile; (3) share able to front the cost, by quintile; (4) adoption by quintile for each delivery mode at equal public cost; (5) cost per retrofit by delivery mode. Plus a sensitivity view showing which assumptions would reverse the result. Regressivity should emerge from the mechanism, not be assumed.

**Variant.** Energy community: no unanimity; joining an existing local community lowers the cost to the next joiner. Data model groups households by local power cabin from day one.

## 5. paperdolls upgrade

This is now a first-class workstream. Work happens in `scifieconomicslab/paperdolls`, on a branch, with changes that are useful to any model (the Great Retrofit is the first client, not the only one).

### 5.1 Architecture overview

```
┌────────────────────────── paperdolls host page ──────────────────────────┐
│                                                                           │
│  Scene (OSM → scene.json)       Model pack (manifest + runtime)           │
│        │                              │                                   │
│        ▼                              ▼                                   │
│  ┌───────────┐   entities     ┌────────────────┐   params / events       │
│  │ Scene ↔   │◄───────────────│ Runtime adapter │◄──────────┐            │
│  │ model     │  bindScene()   │ (js | pyodide | │           │            │
│  │ binding   │                │  remote)        │           │            │
│  └─────┬─────┘                └────────┬────────┘           │            │
│        │ frame state                   │ frames             │            │
│        ▼                               ▼                    │            │
│  ┌───────────┐              ┌──────────────────┐   ┌────────┴─────────┐  │
│  │ Renderer  │◄─────────────│  Store (params,  │──►│ UI shell:        │  │
│  │ (vizlib)  │  visual      │  time, selection,│   │ panels from      │  │
│  │ + picking │  mapping     │  frames, series) │   │ manifest layout  │  │
│  └───────────┘              └──────────────────┘   └──────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

Everything in the page flows through one **store**. Controls write parameters; the runtime reads them and writes frames; the renderer and charts read frames. No component talks to another directly, so a pack can add or replace any of them.

### 5.2 The model pack

A pack is a folder with a manifest and a runtime. It replaces the current `render.yaml` + Python-only model path for interactive use (the current replay path stays for batch/recorded use and remains supported).

```
packs/great-retrofit/
  pack.yaml            # manifest: params, controls, layout, mappings, presets
  runtime.js           # JS implementation (optional if pyodide/remote)
  model.py             # reference implementation (optional here; used by pyodide/remote/tests)
  bind.js              # bindScene(scene) → entities  (model-from-scene)
  components/          # optional custom UI components
  tests/               # golden trajectories
```

**Manifest (sketch):**

```yaml
id: great-retrofit
title: The Great Retrofit
runtime: {type: js, entry: runtime.js, stepsPerYear: 12, horizonYears: 15}

params:                                   # typed, validated, with units and help text
  deduction_rate: {type: number, min: 0, max: 1, default: 0.3, unit: share, label: Rebate rate,
                   help: "Share of retrofit cost deductible from tax", group: Fiscal}
  refundable:     {type: boolean, default: false, group: Fiscal}
  rebate_lag:     {type: number, min: 0, max: 24, default: 12, unit: months, group: Fiscal}
  credit_access:  {type: enum, values: [income_tested, open, none], default: income_tested, group: Credit}
  loan_rate:      {type: number, min: 0, max: 0.08, default: 0.04, group: Credit}
  delivery_mode:  {type: enum, values: [rebate_market, passthrough, public_service], default: rebate_market, group: Delivery}
  vendor_margin:  {type: number, min: 0, max: 0.4, default: 0.15, group: Delivery}
  public_overhead:{type: number, min: 0, max: 0.4, default: 0.10, group: Delivery}
  public_capacity:{type: number, min: 0, max: 1, default: 0.5, label: Public service capacity, group: Delivery}
  means_test:     {type: boolean, default: false, group: Delivery}
  energy_scenario:{type: enum, values: [flat, rising, shock], default: rising, group: Energy}

presets:
  - {id: rebate-only,    label: Rebate only,          params: {delivery_mode: rebate_market, deduction_rate: 0.5}}
  - {id: passthrough,    label: Pay the vendor direct, params: {delivery_mode: passthrough}}
  - {id: public-service, label: Public retrofit service, params: {delivery_mode: public_service}}

entities:                                  # what the model emits per frame
  building:  {fields: {state: category, tenure: category, adopted_share: number, units: int, income_q_mean: number}}
  household: {fields: {income_q: int, retrofit_state: category}}   # only in inspector, never drawn on a street

mappings:                                  # extends today's replay.mapping
  - {entity: building, field: state,          channel: wall,    scale: {type: categorical, values: {...}}}
  - {entity: building, field: tenure,         channel: marker,  scale: {type: categorical, ...}}
  - {entity: building, field: adopted_share,  channel: segments, scale: {type: sequential, ...}}   # new channel: units retrofitted in a condo
  - {entity: building, field: state,          channel: overlay, scale: {...}}

series:                                    # time series for charts
  adoption_by_quintile: {x: year, y: [q1,q2,q3,q4,q5], unit: share}
  rebate_per_euro:      {x: quintile, y: ratio}
  can_front_cost:       {x: quintile, y: share}
  cost_per_retrofit:    {x: delivery_mode, y: euros}

layout:                                    # declarative panels
  left:   [{control: params, groups: [Fiscal, Credit, Delivery, Energy]}, {control: presets}]
  right:  [{chart: line,  series: adoption_by_quintile}, {chart: bar, series: rebate_per_euro},
           {chart: bar, series: can_front_cost}, {chart: bar, series: cost_per_retrofit},
           {chart: kpis, items: [public_cost, bills_saved]}]
  bottom: [{control: timeline}]
  inspector: {building: [header, units_table, why_not_retrofitted]}
  banner: "Geometry from OpenStreetMap. Households and incomes are synthetic."
```

A manifest-only change should be enough to add a slider, a chart, or a new colouring.

### 5.3 Runtime adapter interface

One interface, three implementations (`js`, `pyodide`, `remote`).

```
init(params, entities, seed)  → handle
setParams(handle, params)     → resets or branches, per pack policy
step(handle, n)               → frames[]          // frame = {t, entities patch, series point}
run(handle, toT)              → frames[]          // batch to horizon, used on slider release
snapshot / restore(handle)    → state             // for scrubbing and A/B compare
```

Rules carried over from today's hook: runtimes are deterministic given `(params, seed)`, and rendering never draws from the model's random generator. The existing `paperdolls check` tests (same-seed reproducibility, one state per building, aggregates reconcile) become part of the pack test harness and run on every runtime.

### 5.4 UI component registry

Built-in components: parameter groups (slider, toggle, enum, numeric with unit), preset buttons, play/pause/speed/timeline, legend (auto-generated from mappings, as now), line/bar/stacked chart, KPI tiles, table, inspector, A/B compare toggle (show two parameter sets side by side or overlaid), notes/banner, and the existing rendering switches (detail, ink, fog, pixel) moved into a "Display" group.

Custom components: a pack registers a component with a small contract:

```js
PaperDolls.registerComponent('my-component', {
  props: {...},                        // declared in manifest
  mount(el, store) {...},              // read store state, subscribe, write via store.setParam / store.select
  unmount() {...}
});
```

Implementation: plain DOM and small custom elements, no framework dependency, to preserve the offline single-file build. Charts use a small embedded SVG chart module (no external CDN).

### 5.5 Engine and format changes

Grouped by need; each has a test in `viz/test_*.js` or `tests/`.

**Scene ↔ model binding (new, needed first)**
- Export a clean **scene entity table**: id, centroid, footprint polygon, area, storeys (with `assumed` flag), height, type, adjacency (shared walls / neighbours within X m), street, elevation. This feeds `bindScene`.
- `bindScene(scene)` contract in the pack: returns entities (buildings with units) and the entity-to-scene-id map. Replaces "model building k goes on k-th building by distance".
- Selection of which scene buildings are residential (OSM `building=*` and `landuse`), with an explicit report of exclusions.

**Live rendering**
- Frame-patch API: apply per-building state changes without rebuilding the scene; recolour via the existing sprite cache keyed by `(archetype, heading, colour state)`, so a state change costs one sprite build per distinct state, not per building.
- Redraw budget: a patch touching thousands of buildings must keep a frame under ~50 ms (current settled frames are 5-17 ms on 12k-building scenes; verify).
- Deterministic scene seed separate from model seed (known issue 15).

**New visual channels**
- `segments`: building face split into N parts to show unit state in a block (e.g. 6 windows lit for 6 units, filled as each retrofits). Needed to show partial retrofit in a condo.
- `height` channel (known gap in replay-mapping.md), optional, for quantities like energy use.
- `outline` / `halo` for selection and for highlighting buildings that cannot retrofit (for example, no credit access).
- Overlays from a pack: `scaffold` exists; add `insulation` (wrap/cladding colour change on retrofit) and `solar`/`community` markers as needed.
- Heat-style district layer: ground tint by neighbourhood aggregate (adoption rate, income quintile), for the "who is left behind" view.

**Interaction**
- **Picking:** screen point → building (hit-test on cached sprite bounds + footprint polygon). Hover tooltip and click inspector.
- Selection state in the store; inspector panel reads entity detail from the runtime on demand (so we don't ship every household's data on every frame).
- Keyboard and touch: pan/zoom already exist; add Esc to clear selection, arrow keys to step.

**Terrain**
- Evaluate elevation first: check `vizlib.js` for any vertical offset support. If the ground is flat, add a per-building and per-road-segment `z` offset from a DEM and a gentle ground shading ramp. If full terrain is too costly, ship a "relief shading" ground layer and a documented limitation. Decide after a one-day spike.

**Scale and performance**
- Whole Jette (not a bounding box). Rough estimate: 10k-15k buildings. Run `scale_bench.js` on it. Frame patches, charts and runtime step must not block the main thread: run the runtime in a Web Worker for `js` and `pyodide`.

**Ingest**
- Whole-commune run, with the administrative-boundary clip. Fix what breaks (relations, XML, GeoJSON untested live).
- Better storeys: look for Brussels open building data (heights) to replace the ~100% assumed storeys. Fall back to OSM `building:levels` and the existing assumption report.
- Residential vs non-residential classification and block adjacency.

**Model interface**
- Version the interface. `model-interface v2` = the pack contract above. `v1` (Python hook, four states) stays for recorded replays. `paperdolls check` becomes pack-aware.
- Remove the hard-coded retrofit legend assumptions (known issue: the vendored model's legend names) in favour of manifest-declared labels.

**Output / distribution**
- `paperdolls pack build packs/great-retrofit --scene jette.json --out jette_retrofit.html`: single self-contained offline HTML (as `viewer_built.html` is today).
- `paperdolls pack dev`: local dev server with hot reload of manifest and runtime, for faster iteration with the economists.
- `paperdolls pack check`: manifest validation (unknown params, missing scales, unlabeled legend entries), runtime determinism, JS-vs-Python parity.

### 5.6 Phases for the paperdolls workstream

| ID | Work | Depends on | Demo at end |
|---|---|---|---|
| P1 | Pack manifest schema + validator; store; runtime adapter (`js`); minimal shell (params + timeline + legend) driving the existing renderer with a toy model | none | Toy epidemic with live sliders on the synthetic placeholder area |
| P2 | Frame-patch API + sprite cache keyed by state; Web Worker runtime | P1 | Live re-run on a 12k-building scene without stutter |
| P3 | Scene entity table, `bindScene`, residential classification | P1 | Jette scene where each building shows its model type/units |
| P4 | Picking, selection, inspector, tooltip | P2, P3 | Click a block, see unit table |
| P5 | Charts, KPI tiles, presets, A/B compare, display group | P1 | Full dashboard around the map |
| P6 | New channels: `segments`, `outline`, `insulation` overlay, ground tint | P2 | Condo shows 5 of 6 units retrofitted |
| P7 | Terrain spike → elevation and relief | P3 | Jette hills visible |
| P8 | Whole-commune ingest + better storeys | none | Whole Jette scene with an assumptions report |
| P9 | Pyodide and `remote` runtimes; pack dev server; pack build/check CLI | P1 | Same pack runs on three runtimes with identical output |
| P10 | Custom component registration + docs ("write a pack in an afternoon") | P5 | A second, unrelated pack built by someone else |

Docs deliverable for the paperdolls repo: `docs/pack-spec.md` (manifest reference), `docs/runtime-interface.md`, `docs/components.md`, and a "write your first pack" tutorial using the toy epidemic.

## 6. Phases for the whole project

Phase numbers here are project phases; P-numbers above are paperdolls tasks.

### Phase 0: spec and decisions (about 1 week)
- Send the economist questions; hold a 1-hour working session on the answers.
- Write the v3 model spec (variables, equations, scope).
- Decide the paperdolls branching strategy: work on a branch of `scifieconomicslab/paperdolls`, vendor to this repo only when stable. Decide how this repo consumes it (git submodule or `vendor/` pin with a version check, which also fixes known issue 6).
- Decide v2's fate for the demo (out of scope is acceptable).

### Phase 1: v3 core in Python (about 2 weeks)
- `v3/src/retrofit_v3/` in the repo's existing conventions. Tests: seed reproducibility; state-count conservation; rebate never exceeds cost or tax payable; shared-part measure passes only at the voting threshold; retrofit never exceeds financing (savings plus credit) unless pass-through or public service; public service never exceeds its capacity; monotonicity (higher subsidy never lowers adoption); zero-savings world gives zero adoption.
- `scripts/sweep_v3.py`: subsidy × income sweep.
- **Go/no-go:** does a rebate-only policy reproduce a regressive pattern, and which lever closes it? If not, take the finding to the economists before more UI work.

### Phase 2: paperdolls P1, P3, P8 (about 2-3 weeks, parallel with Phase 1)
Shell + store + `js` runtime on a toy model; scene entity table and `bindScene`; whole-commune ingest.

### Phase 3: calibration (about 1-2 weeks, parallel)
Parameter table with value, source, confidence. Brussels default preset. Sources to look for (availability not yet verified): fiscal income by sector, housing stock by type and tenure, building age and energy performance data, retrofit cost and savings per m², actual Belgian/Brussels rebate rules, energy prices.

### Phase 4: Great Retrofit pack, first live version (about 2 weeks)
Port v3 to JS; golden-trajectory parity test; pack manifest with levers, presets, dashboard; wire to Jette scene. Needs P2, P4, P5 from paperdolls.

### Phase 5: visual depth (about 2 weeks)
`segments` and `insulation` channels, ground tint, terrain, A/B compare. Policymaker-oriented story presets.

### Phase 6: energy community variant (about 2 weeks)
Second runtime module in the same pack, a separate tab with its own parameter group and charts. Tests that the pack abstraction needed no host changes (or note which it needed).

### Phase 7: hardening and handoff (about 1 week)
Dry runs with 2-3 outside people; on-screen "what this model does and doesn't claim"; pack docs; frozen releases; demo video; P10 (custom components, second-pack test).

## 7. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Regressivity result does not emerge from the mechanism | Demo story fails | Go/no-go at end of Phase 1 |
| Pack abstraction over-engineered before a second client exists | Wasted effort, brittle API | Build P1 against the toy model and the Great Retrofit at once; keep manifest small; defer custom components (P10) until the end |
| JS/Python drift | Two models diverge | Shared PRNG, golden trajectories, parity test in CI |
| Live re-render too slow on whole Jette | Sliders feel broken | Frame-patch API (P2), Web Worker, measure on the whole commune early |
| Synthetic households read as real | Ethical and political risk | Show only block-level aggregates on the map; household detail only in a labelled "synthetic example" inspector |
| paperdolls is someone else's repo/plugin | Merge friction, scope disagreement | Agree branching and ownership in Phase 0; keep changes general, with tests |
| OSM coverage and asset fit are weak (28% fit) | Rough-looking map | Accept extrusions; improve storeys with Brussels building data if found |
| Elevation harder than expected | Schedule | One-day spike first; fall back to relief shading |
| Calibration data unavailable at fine granularity | Credibility | Stylised presets with confidence labels |
| Scope creep across three ownership types, three delivery modes and the energy community | Delays | Start with owner-occupied homes and condos, rebate mode first, then pass-through and public service; rental buildings in v2 of the model |

## 8. Dependencies

```
Phase 0 ─┬─► Phase 1 ──► go/no-go ─┐
         ├─► Phase 2 (P1,P3,P8) ───┼─► Phase 4 ─► Phase 5 ─► Phase 6 ─► Phase 7
         └─► Phase 3 ──────────────┘
```

Phases 1-3 touch different folders and can run in parallel. Anything in Phase 4 that needs P2, P4 or P5 can start as soon as those land.

## 9. Immediate next steps

1. Send the revised economist questions (30, with ten priorities).
2. Fork/branch paperdolls and start P1 against the toy epidemic.
3. Run the whole-commune Jette ingest and record what breaks (P8).
4. Draft the v3 spec as soon as the answers on tenure, voting rule and cost sharing arrive.
