# Frame schema (v1)

The contract the paperdolls model pack consumes. Defined in `src/retrofit_v3/frames.py` (TypedDicts, JSON-serialisable). `run_simulation(params, on_step)` calls `on_step(frame)` once at `t = 0` (initial state) and after each of `horizon_months` steps, so `horizon_months + 1` frames. The JS port must emit the same shape.

Stability rule: fields may be added; none may be renamed or removed without bumping `FRAME_SCHEMA_VERSION` (`schema`). A test checks that every field is documented here.

## Frame

| Field | Type | Meaning |
|---|---|---|
| `schema` | int | `FRAME_SCHEMA_VERSION` |
| `t` | int | months elapsed (0 = before any decision) |
| `year` | float | `t / 12` |
| `buildings` | list of building | one entry per model building, in input order |
| `series` | series point | aggregates at this `t` |

## Building (per building, per step)

| Field | Type | Meaning |
|---|---|---|
| `id` | str | scene building id (from `scene_entities`) |
| `state` | str | `not_retrofitted` (no unit done), `partial` (some), `retrofitted` (all), `not_modelled` (rental stub) |
| `tenure` | str | `owner_occupied`, `condo`, `rental` |
| `units` | int | dwelling units |
| `adopted_share` | float | retrofitted units / units, in [0, 1] |
| `income_q_mean` | float | mean income quintile (1..5) of the building's households. Static; block-level only, never household detail |

`state` counts always sum to the number of buildings (`series.state_counts`).

## Series point (`series`)

Quintile arrays have 5 entries, index 0 = lowest income quintile. `null` means undefined (no one to average over).

| Field | Type | Meaning |
|---|---|---|
| `adoption_by_quintile` | float[5] | share of units retrofitted so far (rental units count in the denominator) |
| `rebate_per_euro` | (float or null)[5] | public transfer entitled per euro of price, over adopters so far. Rebate mode: rebate / price (below 1, falls with tax capacity). Passthrough and public service: 1.0 (state pays the full price) |
| `can_front_cost` | (float or null)[5] | among not-yet-retrofitted, non-rental units: share that could finance the current price now (savings plus credit). Ineligible units count as no. Always 1.0 for passthrough/public service for eligible units |
| `cost_per_retrofit` | float or null | mean price paid per retrofit so far. A pack compares modes by running each mode and reading this; the frame carries only the active mode |
| `public_cost` | float | cumulative euros paid by the state: vendor payments at adoption plus rebates when they arrive |
| `bills_saved` | float | cumulative household energy bills saved by retrofits |
| `state_counts` | object | building state -> count |
| `adopted_units` | int | retrofitted units so far |

## Mapping to the pack manifest (plan §5.2)

`entities.building.fields` = `state`, `tenure`, `adopted_share`, `units`, `income_q_mean`; `series` = the first four above; KPI tiles = `public_cost`, `bills_saved`. Results from placeholder parameters must carry the on-screen caveat.
