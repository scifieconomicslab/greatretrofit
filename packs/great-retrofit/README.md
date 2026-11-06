# The Great Retrofit: model pack

A paperdolls model pack for the v3 retrofit model: sliders for the rebate, credit, delivery mode and energy path, and a map of Jette that colours buildings by retrofit state.

**Every number is a placeholder.** The defaults are stand-ins so the structure runs ([v3/docs/placeholders.md](../../v3/docs/placeholders.md)). Nothing this pack shows is a finding, and no regressivity (or any other result) may be quoted from it. The manifest banner says so on screen.

## What works

| Piece | State |
|---|---|
| `runtime.js` | Complete JavaScript port of v3 (npv, financing, rebate, credit, ownership and delivery strategies, scene-entities, the monthly loop). All randomness goes through `v3/js/prng.js`. Frames follow [v3/docs/frame-schema.md](../../v3/docs/frame-schema.md). Registers as `great-retrofit` when `PaperDolls` is present. |
| Parity | `tests/cases.json` holds 10 parameter sets (every delivery mode, every credit setting, refundable, means test, explicit buildings). Python writes golden trajectories to `tests/golden/`; Python and JS must both reproduce them (exact for integers, strings and states; 1e-9 for floats). |
| `pack.yaml` | Valid against the paperdolls validator (`paperdolls pack check`): params in Fiscal / Credit / Delivery / Energy groups, three presets, entity fields, wall and overlay mappings, series, layout, banner. The runtime also passes `PackRuntime.checkRuntime` (deterministic, frames match the manifest) for the defaults and each preset. |
| `bind.js` | `bindScene(scene, {sceneSeed, rules})` turns scene buildings into model buildings and units. Takes the older scene format (`id, footprint, levels`, area computed from the footprint, residential assumed) and the newer fields (`area, height, residential, neighbours`) when they exist. Returns a report listing exclusions and every assumption made. |

## What is placeholder or missing

- All economics: rebate rate, lag, vendor margin, public overhead and capacity, credit rule, income and savings distributions, costs, savings per m2, energy paths, discount rate, consideration probabilities.
- Rental buildings are a stub (shown as "not modelled yet"); condo shared-part voting and cost splitting, canvassing, moving and rebate carry-forward are not implemented. See the placeholders list.
- `pack.yaml`: `chart`, `kpis` and `segments` entries are planned in the paperdolls shell (P5, P6) and produce validator warnings; they are not drawn yet. Until then the timeline bar shows the latest series point.
- `cost_per_retrofit` is for the active delivery mode only. To compare modes, run each preset and read it.
- The shell (P1) places entities on scene buildings in an invented order and does not yet pass `bindScene` output to `init`. When it does (P3), `runtime.js` already takes `entities.building.specs` (the `bindScene` result under `entities`); otherwise it makes a synthetic scene of `entities.building.count` (200) buildings.

## Try it

Needs the paperdolls branch `claude/model-packs-6a7453` (pack shell P1) or later.

```bash
node packs/great-retrofit/tools/bundle.js          # writes dist/ (prng + runtime + bind in one entry; not committed)
cd <paperdolls checkout> && python3 -m paperdolls pack check <this repo>/packs/great-retrofit/dist
python3 -m paperdolls pack build <this repo>/packs/great-retrofit/dist --out retrofit.html [--scene jette.json]
```

The bundle is needed because the paperdolls build inlines only `runtime.entry`. Open `retrofit.html` offline.

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
