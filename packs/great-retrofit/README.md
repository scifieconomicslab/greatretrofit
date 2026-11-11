# The Great Retrofit: model pack

A paperdolls model pack for the v3 retrofit model: sliders for the rebate, credit, delivery mode and energy path, and a map of Jette that colours buildings by retrofit state.

**Every number is a placeholder.** The defaults are stand-ins so the structure runs ([v3/docs/placeholders.md](../../v3/docs/placeholders.md)). Nothing this pack shows is a finding, and no regressivity (or any other result) may be quoted from it. The manifest banner says so on screen.

## What works

| Piece | State |
|---|---|
| `runtime.js` | Complete JavaScript port of v3 (npv, financing, rebate, credit, ownership and delivery strategies, scene-entities, the monthly loop). All randomness goes through `prng.js` (a pack-local copy of `v3/js/prng.js`). Frames follow [v3/docs/frame-schema.md](../../v3/docs/frame-schema.md). Registers as `great-retrofit` when `PaperDolls` is present. |
| Parity | `tests/cases.json` holds 24 parameter sets (every delivery mode and credit setting, refundable, means test with and without market fallback, rebate lag 0 and fractional, explicit buildings, condo peer effect on/off, shared-part votes at 2/3 and 100%, public-service capacity with shared parts, canvassing, tenure overrides) plus two scene-table cases. Python writes golden trajectories to `tests/golden/`; Python and JS must both reproduce them (exact for integers, strings and states; 1e-9 for floats). |
| `pack.yaml` | Valid against the paperdolls validator (`paperdolls pack check`): params in Fiscal / Credit / Delivery / Energy / Condo / Tenure groups, four presets, entity fields, wall, roof and overlay mappings, series, a dashboard layout (line and bar charts by income quintile, KPI tiles, A/B compare), banner. The runtime also passes `PackRuntime.checkRuntime` (deterministic, frames match the manifest) for the defaults and each preset. |
| `bind.js` | `bindScene(scene, {sceneSeed, rules})` turns scene buildings into model buildings and units. Takes the older scene format (`id, footprint, levels`, area computed from the footprint, residential assumed) and the newer fields (`area, height, residential, neighbours`) when they exist. Returns a report listing exclusions and every assumption made. |

## What is placeholder or missing

- All economics: rebate rate, lag, vendor margin, public overhead and capacity, credit rule, income and savings distributions, costs, savings per m2, energy paths, discount rate, consideration probabilities.
- Rental buildings are a stub (shown as "not modelled yet"); moving and rebate carry-forward are not implemented. Condo shared-part voting with floor-area cost splitting, the neighbour effect and canvassing are implemented in both languages ([v3/docs/model-spec.md](../../v3/docs/model-spec.md) §5). See the placeholders list.
- Charts, KPI tiles and A/B compare are drawn by the paperdolls shell from P5/P6 on (checked in [docs/verification/jette-integration.md](../../docs/verification/jette-integration.md), addendum). Known layout and readout issues are listed there and in [docs/verification/merged-build-gaps.md](../../docs/verification/merged-build-gaps.md).
- `cost_per_retrofit` is for the active delivery mode only. To compare modes, run each preset and read it.
- With a scene, `hook.js` hands the `bindScene` result to `init` (as `entities.building.specs`), so each model building stands on a real scene building. Without a scene, the runtime makes a synthetic scene of `entities.building.count` (200) buildings. A scene with no residential building stops with a message instead of falling back to synthetic buildings.

## Try it

Needs a paperdolls checkout with the pack shell (P1) or later; the Jette page was last built against paperdolls `main` (see the verification docs). For the whole commune of Jette, use `scripts/build_jette_demo.sh` from the repository root.

```bash
cd <paperdolls checkout> && python3 -m paperdolls pack check <this repo>/packs/great-retrofit
python3 -m paperdolls pack build <this repo>/packs/great-retrofit --out retrofit.html [--scene jette.json]
```

No bundling step: `runtime.files` in `pack.yaml` lists `prng.js`, `hook.js`, `runtime.js`, `bind.js` in load order and the build inlines them. `prng.js` is a copy of `v3/js/prng.js` (a pack folder must be self-contained); `tests/test_prng_copy.py` fails if the two differ and runs the shared PRNG vectors against the copy. After changing the PRNG: `cp v3/js/prng.js packs/great-retrofit/prng.js`. Open `retrofit.html` offline.

## Tests

```bash
pytest packs/great-retrofit/tests      # parity (Python + node), bind.js, manifest
node packs/great-retrofit/tests/test_parity.js
node packs/great-retrofit/tests/test_bind.js
python3 packs/great-retrofit/tools/regen_golden.py   # only after a deliberate change to the Python model or the cases; review the diff
```

`test_pack.py` finds the paperdolls validator through `PAPERDOLLS_DIR` or the sibling checkout, and needs PyYAML; without them it skips. `tests/fixtures/pack.schema.json` is a copy of the JSON Schema (commit noted in `tests/fixtures/README.md`), used when `jsonschema` is installed. Node tests skip when node is absent.

## JS and Python differences to know

Python's `round` is half-to-even and `sum` of floats is compensated (3.12); `runtime.js` mirrors both (`pyRound`, `pySum`). Transcendental functions (`pow`, `log`, `cos`, `exp`) may differ in the last digit between engines, which is why floats are compared with a tolerance.
