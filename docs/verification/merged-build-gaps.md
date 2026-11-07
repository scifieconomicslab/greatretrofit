# Merged build: the gaps that were left, closed (2026-11-07)

Branch `claude/gr-verify2-f0d44a` from `main` e01212f; paperdolls `main` 6b74ff7 (read-only, not edited). Nothing here is an economic result.
Machine: RTX 3080 + RTX 4080 SUPER, Chromium 1243 from the playwright cache, X11 display `:0`, 16 cores. **Other sessions were running tests and benchmarks on the same machine during the frame-time runs** (load average 4-9 on 16 cores, recorded per run as `loadavg_before` in the JSON), so read small differences as noise.

| # | Item | Result |
|---|---|---|
| 1 | GPU-backed run | **Verified, and it found a major problem**: with GPU canvas the far view runs at about 1 fps (paperdolls bug P1) |
| 2 | `ENRICHED=1` through the script | **Verified**; no script bug |
| 3 | Real-elevation images | **Bug found**: outlines/halos ignore ground height (paperdolls bug P2); terrain faceting (P3); no other defect seen |
| 4 | Phone layout, merged | **Verified with small defects** (tap targets, inspector covers the map, compare far down) |
| 5 | Skipped tests | **Verified**: 2 skips, both environment, neither a hidden failure |
| 6 | Unbundled pack build | **Done**: `pack check`/`pack build` run on `packs/great-retrofit` directly |

## 1. GPU-backed run

**How GPU rasterisation was reached** (`scripts/chrome_flags.mjs`, `GPU=` env on all three browser scripts; `GPU=none` stays the default and is the old behaviour):

| `GPU=` | flags | what Chromium reported (`SystemInfo.getInfo`, saved in each JSON as `gpu`) |
|---|---|---|
| `none` | `--headless=new --disable-gpu` | SwiftShader; compositing and rasterisation `disabled_software` |
| `vulkan` | `--headless=new --use-angle=vulkan --enable-features=Vulkan --ignore-gpu-blocklist --enable-gpu-rasterization` | ANGLE on the NVIDIA Vulkan driver, **RTX 4080 SUPER**; rasterisation `enabled_force`, but **compositing stays `disabled_software`** and canvas drawing behaved like software (same numbers as `none`). Counts as GPU raster, not as a GPU canvas |
| `egl` | `--headless=new --use-gl=angle --use-angle=gl-egl --ignore-gpu-blocklist --enable-gpu-rasterization` | ANGLE, `NVIDIA GeForce RTX 4080 SUPER/PCIe/SSE2, OpenGL ES 3.2 NVIDIA 580.178.04`; compositing `enabled`, rasterisation `enabled_force`. **Real GPU path** |
| `x11` | headful on `:0`, `--ignore-gpu-blocklist --enable-gpu-rasterization` | ANGLE OpenGL 4.5 NVIDIA 580, RTX 4080 SUPER; compositing `enabled`. Chromium's own desktop path (a window appears briefly). Run once (plain, DPR 1) |

The 3080 was not used (Chromium picked the 4080 SUPER).

**Frame times** (`scripts/measure_frames.mjs`; table of every run: [gpu/frames_table.md](gpu/frames_table.md), raw: `gpu/frames_*.json`; cell = fps (p50 / p95 ms between rAF callbacks), 1440x900 window, map canvas 763x437 css). Far = whole commune; near = 7 wheel notches in. Idle 2 s, playing 4 s at 24 months/s, slider drag 3 s, wheel zoom = 10 rounds of 3 notches in, 3 out (so "wheel zoom at far" is not purely far).

Selection (full table in the file). The columns are fps:

| zoom | scene | DPR | software (`none`) idle / play / drag / wheel | GPU canvas (`egl`) idle / play / drag / wheel |
|---|---|---|---|---|
| far | plain | 1 | 3.1 / 22.5 / 40 / 58 | **1.1 / 1.0 / 1.0 / 1.2** |
| far | plain | 2 | 2.4 / 2.0 / 2.2 / 25 | **0.8 / 0.9 / 0.9** / 47 |
| far | enriched | 1 | **2.1 / 1.8 / 1.9** / 38 | **0.8 / 0.7 / 0.7 / 0.8** |
| far | enriched | 2 | **2.0 / 1.9 / 2.0** / 36 | **0.9 / 0.8 / 0.9 / 0.9** |
| near | plain | 1 | 60 / 60 / 60 / 60 | 55 / 59 / 60 / 56 |
| near | plain | 2 | 59 / 23 / 55 / 60 | **2.6** / 24 / 44 / 60 |
| near | enriched | 1 | 52 / 50 / 56 / 60 | 32 / 43 / 45 / 60 |
| near | enriched | 2 | 60 / 25 / 55 / 60 | **2.4 / 2.5 / 2.3** / 24 |

Findings:
1. **The "built-in browser pane is slow because of its compositor" explanation was wrong.** Any Chromium with GPU-accelerated Canvas2D (`egl`, headful `x11`) draws the far view at **about 1 fps** (one frame every 1.2-2 s), and near at DPR 2 at 2-3 fps in places. That matches the pane's 1-3 fps. Software rendering is 20-60x faster at far zoom on the plain scene.
2. Cause isolated: `IDLE_ONLY=1 GPU=egl` on the plain page: 0.9 fps. Adding `--disable-accelerated-2d-canvas`: **23.2 fps**. Rewriting the built page so every `getContext('2d')` in the draw path uses `{willReadFrequently: true}` (software canvas) under `egl`: **22.9 fps**. Doing it for only one group of canvases (layer canvases, stage canvases, or sprite canvases) leaves 0.9 fps; layers + stage + sprites + the two helper canvases at lines 2260/2425 of the built page give 22.4. The main thread is not busy under GPU canvas (no long-animation-frame entries), so the cost is on the GPU side: big layer canvases being drawn and read back (my reading, not profiled further).
3. **Enriched far zoom is about 10x slower than plain in software** (2 fps against 22 fps playing; p50 about 580 ms per frame even idle, where plain idles at 16.7 ms). So enrichment (relief and heights) is not drawn from a cache at far zoom. Near zoom is fine in both.
4. DPR 2 costs mostly while playing (about 23-25 fps both modes, near).
5. Far idle in the old plain numbers (3 fps, p95 380 ms) includes one 360 ms first frame; the steady frames are 16.7 ms.

Caveat: `vulkan` here is not a GPU-canvas run (compositing software), so it mirrors `none`. Reading from one 4080 SUPER; no run on the 3080.

## 2. `ENRICHED=1 scripts/build_jette_demo.sh`, clean

Clean worktree, no `build/`, `cache/`, `data/raw/` (verified by `ls`); python = a fresh venv with shapely, numpy, Pillow, pyyaml (`pip install -e ".[geodata]"` now lists them). One command, 4 min 20 s wall (mostly the WCS tiles), no script change needed:
- Downloads: 58 MB DTM tiles (one HTTP 500, the script's retry succeeded) + 16.7 MB UrbIS 3D zip; Overpass extract 14 MB. `data/raw` is 141 MB on disk because the zip is unpacked (84 MB); download volume is about 75 MB plus the OSM extract. Nothing raw is tracked (`git status` clean apart from my edits).
- Output vs the hand-built scene from the geodata session (`gr-geodata-a1c42a/build`): `jette-elevation.tif` byte-identical (sha dcf6a268…); `jette-scene-enriched.json` 5 942 636 bytes both, 9 214 buildings, identical in every key but `area.generated` (timestamp); `jette-scene-enriched-report.json` identical (98.5% match applied, assumed storeys 98.8% -> 1.5%). Pages built from both scenes are 6 504 926 bytes and differ in **7 bytes** (the timestamp). Page: 6.20 MB, 8 105 of 8 105 model buildings placed on scene buildings (banner text), `binding.bound` true. Screenshots: `docs/images/relief/*`, `docs/verification/phone/*`.

## 3. Relief

Looked at all of `docs/images/geodata/` (hill, overview, tall) and rendered 12 new views of the enriched page: [docs/images/relief/](../images/relief/) (`hill_1/2`, `steep_1/2`, `valley_1/2`, each `_mid` and `_near`; `scripts/render_relief_views.mjs`, locations in `scripts/geodata/relief_locations.json`, picked as the 150 m cells with 40+ buildings that have the highest and lowest mean ground height and the largest spread; ground height in Jette runs 25-82 m).

Judgement: at relief x1 the real elevation reads as mild, not wrong. Buildings sit on the ground (no floating or sunken blocks seen at mid or near zoom), terraces of different height meet cleanly, roads follow the surface, shadows fall consistently, depth order is right. The hill and valley views differ mostly through the ground shade, because Jette's slopes are gentle. Defects:

| # | Defect | Evidence | Owner |
|---|---|---|---|
| P2 | **Outlines and halos (the "cannot pay now" red boxes) are drawn at ground height 0, not at the building's ground height**, so they float below their building on empty ground, by `z x scale` pixels (a building at 63 m is drawn 138 px above its outline at scale 2.18; ~440 px at near zoom). The visibility test `vis()` also uses z=0, so culling is off by the same amount. | `relief/steep_2_mid.jpg` (red boxes on bare ground right of centre), `relief/valley_2_near.jpg`, `relief/hill_1_mid.jpg`. Code: `viz/packhost.js` `outlinePath`, `ringPath`, `vis` call `V.proj(view, x, y, 0 / h / z||0)` without `e.z`; the selection outline `drawHighlight` was patched for `sh.z` but the pack's own channels were not. | paperdolls |
| P3 | Ground is flat-shaded 25 m quads; faint diamond/staircase blocks are visible on grass and, strongly, on the bare land outside the commune (`relief/valley_1_mid.jpg` right half, `relief/hill_1_mid.jpg` top right). The overview images (C, D in `geodata/jette-overview.jpg`) show horizontal streaks at the south corners (DTM coverage edge). Smoothing is a renderer matter; a finer `--terrain-cell` for `ingest` is a data option (costs size). | images named | paperdolls (shading); this repo (could pass a finer `--terrain-cell` in `build_enriched.sh`; not done, size cost not measured) |
| - | No seams, floating or sunk buildings, or road/slope mismatch seen in the 12 views. This is a visual check of six places, not a full audit. | | |

## 4. Phone layout (merged build)

`scripts/verify_jette_phone.mjs`, DPR 2, touch emulation, enriched page; images and `phone_summary.json` in [docs/verification/phone/](phone/).

| check | 390x844 | 768x1024 |
|---|---|---|
| horizontal scroll | none (scrollWidth 390) | none (768) |
| map | 390x421, 50% of the screen height; page height 3 599 px | 768x511, 50%; page 2 711 px |
| first screen | banner (long, 7 lines) then map then timeline; map shows the whole commune small | same, banner 2 lines |
| tap on a building | selected (id 6502), inspector docked over the lower part of the map, fully inside the viewport, scrolls inside (text cut at "tenure") | selected, inspector docked right, 300x427, fully visible |
| tap targets under 40 px (of 49) | 22: range sliders 32 px high (11), checkboxes 22x22 (4 of the display toggles), map-source buttons A/B 35x44, quintile buttons q1-q5 56x36 | same 22 |

Defects (owner paperdolls, the page layout is `viz/packhost.html`): sliders and display checkboxes are below the 40 px guide (checkbox label rows are spaced 47 px but only 22 px is tappable); the 390 inspector hides the lower 40% of the map; the compare section sits below the whole legend, about 2 000 px down the page on a phone; the banner takes a quarter of the first screen. Nothing overflowed and everything reachable.

## 5. Skipped tests

| run | result | skips |
|---|---|---|
| this repo, `.venv` | 148 passed, 1 skipped (includes the two new prng-copy tests) | `tests/geodata/test_geodata.py`: shapely is not installed in `.venv`. Not a failure: with shapely (scratch venv) the geodata tests run and pass (160 passed). **Enable**: `pip install -e ".[geodata]"` (extra added; skip message now says so). I did not install into the shared `.venv`. |
| paperdolls, `.venv` | 296 passed, 1 skipped, 4 min 14 s | `tests/test_ingest.py:557`: needs `cache/jette-bbox-extract.json`, a gitignored 3 MB Overpass extract. I ran the test against a clean `git archive` of 6b74ff7 with that file copied in: **passes**. **Keep as an opt-in data test** (or give it a small committed fixture); do not remove. paperdolls change, not made. |

So the "two skipped" are one per repo, both missing optional inputs.

## 6. Unbundled build

`packs/great-retrofit/pack.yaml` now has `runtime.files: [prng.js, hook.js, runtime.js, bind.js]`; `prng.js` is a copy of `v3/js/prng.js`; `tests/test_prng_copy.py` fails if the bytes differ and runs the shared PRNG vectors on the copy. `pack check packs/great-retrofit`: 0 errors, 1 warning (`units` field declared but not shown by a mapping; pre-existing in kind). `pack build packs/great-retrofit` works with and without `--scene`, and `build_jette_demo.sh` is down to check + build (the enriched run above used it). Removed `tools/bundle.js`, the `dist/` ignore entries; README, the plan (section 5.5 status) and `jette-integration.md` (bug 3 / item H) updated. Parity and bind tests unchanged and green.

## Bugs for the paperdolls round (not fixed here)

- **P1 GPU canvas far-zoom collapse.** Repro: `GPU=egl IDLE_ONLY=1 node scripts/measure_frames.mjs build/jette_plain.html` (0.9 fps), then `CHROME_FLAGS=--disable-accelerated-2d-canvas` (23 fps). Also any headful Chrome on a GPU machine. Fix candidates: `willReadFrequently: true` on every 2D context in the draw path (all of them; groups alone do nothing), or a canvas strategy that does not read back layer canvases per frame.
- **P1b Enriched far zoom 10x slower than plain** (software): `GPU=none IDLE_ONLY=1 node scripts/measure_frames.mjs build/jette_enriched.html` vs `jette_plain.html` (build both per the README steps; scenes in `build/`).
- **P2 Outline/halo/vis ignore `e.z`.** Repro: `node scripts/render_relief_views.mjs build/jette_enriched.html out scripts/geodata/relief_locations.json`, open `out/steep_2_mid.jpg`.
- **P3 Terrain faceting** (images above).
- **P4 Phone layout items** (section 4).

## What I could not verify

Real touch on a physical phone (emulated only); a run on the RTX 3080; whether GPU-canvas slowness also affects other Chromium versions; the cause of P1 below "GPU side, canvases read back" (not profiled with a trace); whether a finer terrain cell removes P3. The frame-time runs shared the machine with other sessions.

## New or changed files

`scripts/chrome_flags.mjs`, `measure_frames.mjs`, `frames_table.py`, `verify_jette_phone.mjs`, `render_relief_views.mjs`; `GPU=` support in `verify_jette_browser.mjs` and `verify_jette_dashboard.mjs`; `scripts/geodata/relief_locations.json`; `docs/verification/{gpu,phone}/`, `docs/images/relief/`; pack changes in item 6; `pyproject.toml` `geodata` extra.
