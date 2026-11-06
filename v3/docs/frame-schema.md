# Frame schema (v1, additive changes since the skeleton)

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
| `shared_state` | str | `none` (no shared parts: owner-occupied, rental, single-unit, or `shared_measure` off), `pending` (vote not passed), `approved` |
| `vote_yes_share` | float | floor-area share of the building's households that support the shared measure now; 0 when `shared_state` is `none` |

`adopted_share` counts a unit as retrofitted when all its parts are paid (its own part and, in a condo with a shared measure, its share of the shared measure). `state` counts always sum to the number of buildings (`series.state_counts`).

## Series point (`series`)

Quintile arrays have 5 entries, index 0 = lowest income quintile. `null` means undefined (no one to average over).

| Field | Type | Meaning |
|---|---|---|
| `adoption_by_quintile` | float[5] | share of units retrofitted so far (rental units count in the denominator) |
| `rebate_per_euro` | (float or null)[5] | public transfer entitled per euro of price, over adopters so far. Rebate mode: rebate / price (below 1, falls with tax capacity). Passthrough and public service: 1.0 (state pays the full price) |
| `can_front_cost` | (float or null)[5] | among not-yet-retrofitted, non-rental units: share that could finance what they still have to pay now (savings plus credit). A household outside the means test is quoted the market price. Always 1.0 for passthrough/public service for households inside the scheme |
| `cost_per_retrofit` | float or null | mean price paid per retrofit so far. A pack compares modes by running each mode and reading this; the frame carries only the active mode |
| `public_cost` | float | cumulative euros paid by the state: vendor payments at adoption plus rebates when they arrive |
| `bills_saved` | float | cumulative household energy bills saved by retrofits |
| `state_counts` | object | building state -> count |
| `adopted_units` | int | retrofitted units so far (all parts paid) |
| `cost_per_retrofit_parts` | object or null | `{base, markup}` over retrofitted units so far: mean labour-and-materials cost, and mean vendor margin or public overhead. `base + markup = cost_per_retrofit` |
| `canvass_hours_by_quintile` | float[5] | mean weekly hours per household spent canvassing (advocates in multi-unit condo buildings only; others 0) |
| `leisure_hours_by_quintile` | float[5] | mean weekly free hours per household left after canvassing; never negative |
| `net_cash_by_quintile` | (float or null)[5] | household cash timeline by quintile: mean cumulative net cash (bills saved + rebates received - savings spent - loan payments made) over households that have paid for any works; null if none yet |
| `shared_counts` | object | `{pending, approved}`: number of buildings with shared parts by vote state |

## Mapping to the pack manifest (plan §5.2)

`entities.building.fields` = `state`, `tenure`, `adopted_share`, `units`, `income_q_mean`; `series` = the first four above; KPI tiles = `public_cost`, `bills_saved`. Results from placeholder parameters must carry the on-screen caveat.
