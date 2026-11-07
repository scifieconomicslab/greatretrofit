# GPU canvas frame rates after the paperdolls fixes (2026-11-07)

Measured by the coordinator, not by the fixing session: `GPU=egl DPR=n node scripts/measure_frames.mjs build/jette_<scene>.html`, pages built from paperdolls `main` at `ca1920d` (fixes for paperdolls #3, #14, #17 to #22) with this repo's pack. Chromium 1243, ANGLE on the NVIDIA RTX 4080 SUPER (`SystemInfo.getInfo`: GPU compositing `enabled`, rasterisation `enabled_force`; saved in each JSON as `gpu`), 1440x900 window, whole commune of Jette (9,214 buildings, 8,105 bound). Frames per second, gaps between requestAnimationFrame callbacks. The machine's load average was 6 to 9 on 16 cores during the runs (other work was running), so read small differences as noise. The RTX 3080 was not used.

## After

| scene | DPR | far idle | far playing | far drag | far wheel | near idle | near playing | near drag | near wheel |
|---|---|---|---|---|---|---|---|---|---|
| plain | 1 | 60.5 | 44.7 | 60.2 | 60.3 | 60.3 | 60 | 59.9 | 60.3 |
| plain | 2 | 57.8 | 44.7 | 60.1 | 60.3 | 60.1 | 59.5 | 60.1 | 60.3 |
| enriched | 1 | 54.8 | 44.4 | 60.2 | 60 | 53.7 | 53.9 | 52.3 | 59.8 |
| enriched | 2 | 60.6 | 43.7 | 60.2 | 59.8 | 60.1 | 58.5 | 60.1 | 60.3 |

## Before (from `merged-build-gaps.md`, same machine and method, paperdolls `6b74ff7`)

| scene | DPR | far idle | far playing | far drag | far wheel | near idle | near playing | near drag | near wheel |
|---|---|---|---|---|---|---|---|---|---|
| plain | 1 | 1.1 | 1.0 | 1.0 | 1.2 | 55 | 59 | 60 | 56 |
| plain | 2 | 0.8 | 0.9 | 0.9 | 47 | 2.6 | 24 | 44 | 60 |
| enriched | 1 | 0.8 | 0.7 | 0.7 | 0.8 | 32 | 43 | 45 | 60 |
| enriched | 2 | 0.9 | 0.8 | 0.9 | 0.9 | 2.4 | 2.5 | 2.3 | 24 |

The target set for the fix was at least 30 fps idle and 24 fps playing at far zoom on a GPU canvas at DPR 1 and 2 on both scenes; it is met in all four configurations (idle 55 to 61 fps, playing 44 to 45 fps; p95 frame 33 to 50 ms while playing).

## Not covered

One GPU (RTX 4080 SUPER), one browser version, headless with a 1440x900 window (not a physical display or a laptop integrated GPU), emulated rather than real DPR 2. Phone and tablet GPUs were not measured. A laptop with an integrated GPU is the likely presenter machine and should be checked before a live demo.
