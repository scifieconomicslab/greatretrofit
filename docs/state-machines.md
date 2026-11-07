# State machines of the v3 model and its JavaScript runtime

Scope: the Python reference `v3/src/retrofit_v3/` and the browser runtime `packs/great-retrofit/{runtime,hook,bind}.js`, with the handle lifecycle the paperdolls shell drives through `viz/packruntime.js` (read-only, `/data/ScifiEconomicsLab/scifirender/paperdolls`).
Analysis and evidence only: no model or runtime code was changed. Every economic number in the model is a placeholder; the figures quoted below show that two code paths disagree, they are not results.

Status words: **CONFIRMED** = deterministic repro that was run (command and observed output pasted); **SUSPECTED** = reasoned, with what blocked a repro; **REFUTED** = code prevents it (line given).
Line numbers are for the commit this branch starts from (`e01212f`).

## 0. Summary: confirmed defects, highest impact first

| Rank | ID | Defect | Impact | Likelihood | Repro |
|---|---|---|---|---|---|
| 1 | SM-1 | `rebate_lag_months = 0` (the slider's minimum, in the manifest range 0..24) loses every rebate: it is queued under the month that has just been processed. "Cumulative public cost" omits all rebates, and household net cash omits them too. Python and JS agree, so no test sees it. A fractional lag (Python API) is lost the same way. | High: the headline public-cost series is wrong for the rebate mode, with no error | High: "no lag" is the natural thing to try | `repro/test_rebate_lag.py`, `repro/js/lag_zero.js` |
| 2 | SM-4 | The means-test help text in `pack.yaml` says the test "Does not apply to the rebate"; the model (Python and JS) applies it to the rebate: an ineligible household buys on the market with no rebate. | Medium: wrong user-facing statement about a lever | Certain (every user who reads the tooltip) | `repro/test_means_test_help_text.py` |
| 3 | SM-7 | A scene whose buildings are all non-residential binds to 0 model buildings, but `paramsFromPack` falls back to the 200 synthetic ones; the first frame then has 200 entries for a declared count of 0 and `start()` throws (with validation off, the wrong-size frame goes through). | Medium: red banner, no run | Low for Jette, medium for other scenes or a filtered scene | `repro/js/zero_residential_scene.js` |
| 4 | SM-8 | A scene building without `id` (ids are optional in a scene) is addressed by bind.js as `"undefined"` and by paperdolls as `"#<index>"`: it is modelled and counted in every series, and never drawn. | Medium: the map and the series disagree, with only a console-level warning | Low for Jette (OSM ids), medium for other scenes | `repro/js/idless_buildings.js` |
| 5 | SM-9 | `toPackFrame` stores `units` and `units_done` in `Int16Array`; a building of more than 32767 dwellings (huge footprint times levels from bad geometry; bindScene has no upper bound) wraps to a negative count. | Medium: negative units in the segments channel | Low | `repro/js/int16_overflow.js` |
| 6 | SM-2 | Python `Params` accepts NaN and +/-inf (`value <= 0`, `value < 0` are False for NaN); some reach the frames as inf. JS rejects NaN. Not reachable from the sliders (finite ranges). | Low via the shell, medium via the API or a future manifest entry | Low | `repro/test_params_nonfinite.py` |
| 7 | SM-3 | Explicit buildings are not validated: zero units or zero area gives a bare `ZeroDivisionError`, an unknown tenure a `KeyError`, negative or NaN areas run silently. Not reachable through bind.js. | Low | Low | `repro/test_degenerate_buildings.py` |
| 8 | SM-10 | JS `Params()` coerces: `null`, numeric strings and `[]` are accepted where Python raises `TypeError`. | Low | Low | `repro/js/params_coercion.js` |
| 9 | SM-13 | (paperdolls, not ours, listed for the hand-off) `PackRuntime.step(0)` after `start()` throws "t is N, expected N+1", although the runtime interface says `step(h, 0)` returns the current frame. The runtime itself is right. | Low | Low | `repro/js/lifecycle_surface.js` |

Behaviours pinned as characterisation tests (they pass today and are questions about the design, not bugs in the code as written): SM-5 votes that reach the threshold but never pass because one owner cannot pay (108 buildings in 200 sampled 180-month runs), SM-6 a household charged for the shared part after its own horizon (1 case in 200), SM-15 empty quintiles drawn as 0 rather than no-data. SM-11, SM-12, SM-14 are lifecycle-surface observations (section 13).

Everything else asked about was attacked and held (section 14: REFUTED list). Python and JS never diverged on 8,000 random cases frame by frame (section 15).

Proposed issue grouping (not filed): **A** rebate queue timing (SM-1); **B** pack text vs behaviour (SM-4); **C** scene/runtime contract (SM-7, SM-8, SM-9); **D** input validation (SM-2, SM-3, SM-10); **E** design questions (SM-5, SM-6, SM-15); **F** lifecycle contract (SM-11, SM-12, SM-13).

## 1. Evidence and how to run it

| What | Where | Command |
|---|---|---|
| Fuzz: invariants on every step, Python | `tests/fuzz/test_fuzz_python.py`, `fuzz_lib.py` | `PYTHONPATH=v3/src .venv/bin/python -m pytest tests/fuzz -q` (about 9 s) |
| Fuzz: Python vs JS frame by frame, adapter typed frames | `tests/fuzz/test_fuzz_parity.py`, `parity_lib.py`, `run_js_cases.js`, `run_js_params.js` | same |
| Fuzz: handle lifecycle programs, emulated snapshot | `tests/fuzz/test_fuzz_js_lifecycle.py`, `lifecycle_fuzz.js` | same |
| Repros | `docs/state-machines/repro/` | `PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro -q -rx` |

The fuzz tests are bounded (`FUZZ_BUDGET_S`=20 s, `FUZZ_N`=150 cases per kind, `FUZZ_PARITY_N`=120, `FUZZ_LIFECYCLE_N`=12) and deterministic; `FUZZ_SEED` shifts the case seeds. A case is `fuzz_lib.case_for(kind, seed)` with `kind` = `manifest` (parameters inside the pack.yaml ranges, lag >= 1) or `edge` (additionally: vote threshold 0.01 and 1, shared share 0 and 1, consideration probability 0 and 1, discount rate 0 and 1, tax rate 0 and 1, savings scale 0 and 50, loan term 1 and 1200 months, cost and saving per m2 at 1e-6 and 1e5, credit multiple 0 and 100, seeds above 2^31, all-rental scenes, single building, one-dwelling buildings, 15 to 40 dwelling condos). Both kinds mix `public_capacity` 0, `credit_access: none` with passthrough, `vote_threshold` 0.5 and 1.0.

Runs made while writing this (all clean, none needs a seed to cite):

* Python invariants (frame, white-box state, event log; section 12): seeds 0..1499 and 10000..12499 of both kinds, 8000 runs, 0 violations. The generators avoid the regions of SM-1 to SM-3 on purpose; those have their own repros.
* Python vs JS: seeds 0..1499 and 10000..12499 of both kinds, 8000 cases, 0 differences in frames, events or votes (tolerance 1e-9 relative), and 0 differences between the adapter's typed frames and a mapping re-derived independently from the Python frame.
* Lifecycle: 40 random programs, 0 problems.
* Existing suite: `PYTHONPATH=v3/src .venv/bin/python -m pytest v3 packs tests -q` gives `154 passed, 1 skipped`.

Note on the existing capacity test: `v3/test_v3/test_invariants.py::test_public_service_respects_capacity` allows a slack of one job per month and in total. The fuzz check recomputes the exact slot count `int(quota + carry)` month by month (`fuzz_lib.event_problems`) and holds with no slack.

## 2. Machine M1: the month step (phase ordering)

Identity: `Simulation.step`, `v3/src/retrofit_v3/model.py:332-414`; JS twin `runtime.js:553-628`. Explicit (the docstring at `model.py:1-14` lists the phases), but the phase order is only a convention in the code.
State: `t` (`self.t`, advanced at `model.py:412`), plus everything in M2 to M8. Python's `run_simulation` (`model.py:417`) emits frame 0 and then `horizon_months` frames. `Simulation` itself has no end: it steps as long as it is called.

| Phase | Lines | Reads | Writes |
|---|---|---|---|
| 1 cash | 335-346 | `pending[t]`, `loans`, `saving_frac`, `horizon` | `public_cost`, `cash_net`, `bills_saved` |
| 2 snapshot | 348-353 | `adopted_in_b`, advocates | local copies only (nobody reacts to this month's decisions) |
| 3 consider | 356-372 | `hash_uniform(seed, uid, t)`, `_evaluate` | `candidates`, `supporter` |
| 4 capacity, pay | 374-383 | `quota`, `carry`, `queue_draw` | `carry`, `_pay` for candidates |
| 5 votes | 385-411 | `_yes_share`, `_evaluate` for every owner | `approved`, `votes`, `_pay(kind="shared")` |
| 6 frame | 412-413 | all | `t`, `frame` |

Invariants: the order 1 (cash) before 4 (new rebates are queued) is what SM-1 breaks for lag 0: phase 1 pops `pending[t]` at line 335, phase 4 pushes to `pending[t + lag]` at line 222; with lag 0 the key is `t`, which was popped already and `t` is never visited again. Phase 3 decisions use savings and tax as of phase 2 (no payments happened yet); phase 5 re-evaluates with the savings left after phase 4, which is why a supporter can end up blocked (SM-5). `hash_uniform(p.seed, u.uid, t)` (line 363) is stateless, so the number of steps taken cannot change a draw: chunking `step(1)` x n vs `step(n)` vs `run(n)` is identical (checked by the lifecycle fuzz).

Reachable invalid transition: **SM-1** (below). Phase 5 charges owners whose horizon has passed (SM-6).

## 3. Machine M2: building state

Identity: `_make_frame`, `model.py:278-299` (JS `runtime.js:505-524`); implicit: the state is recomputed every frame from counters, never stored. Explicit set: `BUILDING_STATES` (`frames.py:10`).
Encoding: `tenure` (after `_retenure`), `adopted_in_b[bi]`, `b.units`.

| State | Condition (first match wins) |
|---|---|
| `not_modelled` | `not _can_adopt(bi)`, i.e. tenure `rental` (`ownership.py:58`) |
| `not_retrofitted` | `adopted_in_b == 0` |
| `partial` | `0 < adopted_in_b < units` |
| `retrofitted` | `adopted_in_b == units` |

There is no other state: the four values are exhaustive and exclusive by construction (the `if/elif` chain). Rental buildings never leave `not_modelled` (their units are skipped at `model.py:359`, and votes need `needs_shared`, which is False for rental, `ownership.py:21`).

Transitions: `not_retrofitted -> partial` when the first unit of the building becomes `complete` (`_pay`, line 243); `partial -> retrofitted` when the last does. No transition back: `complete` is never reset (REFUTED, section 14, R-2). A building with a shared measure can only count a unit as adopted when both its own part and the shared part are paid, so after an approved vote the whole building can jump from `not_retrofitted` to `retrofitted` in one step if every owner had already paid their own part.

Invariants (checked by `fuzz_lib.frame_problems`): `state_counts` sums to the number of buildings; `adopted_share * units` is an integer in `[0, units]`; state follows the count; rental implies `not_modelled`, share 0, shared state `none`; `adopted_units` equals the sum of `adopted_share * units`; adopted units never exceed the units of modelled buildings; `adopted_share` never falls. All held on 8000 runs.

Reachable invalid states: a building with zero units divides by zero at `model.py:299` (SM-3). A building can sit in `partial` for the whole run although everyone wanted the work, because a household whose horizon passed (`t >= u.horizon`, line 359) never considers again; with 5..25 year stays and 15 years of run, `retrofitted` is not reachable for such buildings. Design question, E group, not a code defect.

## 4. Machine M3: dwelling unit

Identity: `_Unit`, `model.py:36-61`; transitions in `_pay` (`model.py:217-248`); implicit (a set of booleans).
State variables: `unit_done`, `shared_paid`, `complete`, `supporter`, `paid_any`, `needs_shared`, plus the clock `t >= horizon` (expired).

States (rows are reachable combinations):

| State | `unit_done` | `shared_paid` | `complete` | Notes |
|---|---|---|---|---|
| U0 open | F | F | F | may consider each month while `t < horizon` |
| U1 own part paid (needs_shared only) | T | F | F | waits for the vote |
| U2 shared part paid first | F | T | F | the vote passed before this unit decided; still considers its own part |
| U3 complete | T | T or not needs_shared | T | terminal |
| UX expired | any | any | F | `t >= horizon`: skipped in phase 3 forever, still charged in phase 5 (SM-6) |
| UR inert | | | F | rental building: never considered |

Transition table:

| From | Event | Guard | To | Side effects | Lines |
|---|---|---|---|---|---|
| U0 | consider (draw < p_consider) | not expired, `unit_base` financeable, NPV > 0, passes capacity | U3 if `not needs_shared` else U1 | `_pay(kind whole/unit)` | 363-368, 382-383 |
| U0, U1 | consider | `needs_shared`, not yet approved, not yet supporter, shared part financeable and NPV > 0 | same state, `supporter = True` | none (no payment) | 369-372 |
| U0 | vote passes in own building | every owner can pay their share | U2 | `_pay(kind shared)` | 396-411 |
| U1 | vote passes | same | U3 | complete: `adopted_in_b`, `q_adopt`, `price_sum`, `base_sum`, `n_complete` | 411, 243-248 |
| U2 | consider, unit part pays | as first row | U3 | as above | 363-368 |
| any not complete | `t` reaches `horizon` | | UX | none | 359 |

Invariants (`fuzz_lib.sim_problems`, every step, 8000 runs, 0 violations): `savings >= 0` (`plan_financing` takes `min(usable, upfront)` with `usable <= savings`, `financing.py:17-18`); `0 <= tax_left <= tax` (`model.py:231` clamps; non-refundable rebate is capped by `tax_payable`, `rebate.py:15`); `complete` iff `unit_done` and (`shared_paid` or not `needs_shared`); `adopted_in_b[b]` equals the number of complete units of `b`; `n_complete = sum(adopted_in_b) = sum(q_adopt)`; no unit pays the same `kind` twice; `shared_paid` implies the building's vote is `approved` and vice versa; no payment in a rental building.

Reachable invalid state: none found in the manifest region. Out of it: NaN or inf parameters give NaN/inf savings, tax and incomes (SM-2).

## 5. Machine M4: condo shared-measure vote

Identity: phase 5, `model.py:385-411` (JS `runtime.js:605-624`); explicit data `approved[bi]`, `unit.supporter`, `VoteEvent`; the frame exposes it as `shared_state`.
Applies when `shared_measure` is on and the tenure has shared parts: `Condo.has_shared_parts` is `units >= 2` (`ownership.py:50`); a one-unit condo, an owner-occupied building with several explicit units and rental buildings have none (`needs_shared[bi]` False, `model.py:128`).

States of a building: `none` (no shared parts), `pending` (vote not passed), `approved`. Variables: `needs_shared[bi]`, `approved[bi]`, per-unit `supporter`, floor-area share `_yes_share` (`model.py:250`).

| From | Event | Guard | To | Side effects | Lines |
|---|---|---|---|---|---|
| pending | unit considers and likes the shared part | not yet supporter, financeable, NPV > 0 | pending (yes share rises) | `supporter = True`, never withdrawn | 369-372 |
| pending | end of month | `yes + 1e-9 >= vote_threshold` | (continue) | | 388-390 |
| pending | | public service only: `ceil(units * shared_share - 1e-9) <= slots_left` | (continue) | `slots_left` reduced on success | 391-395, 407-408 |
| pending | | every owner can finance their share (`_evaluate` is not None for all) | approved | `votes.append`, `_pay(kind shared)` for every owner, regardless of NPV | 396-411 |
| pending | | some owner cannot pay | pending, blocked | nothing, retried next month | 400-405 |
| approved | any | | approved | terminal | 386 |

Invariants (checked): `vote_yes_share` in `[0,1]`; a recorded vote never has `yes_share < threshold`; approval implies every owner paid `shared` and the converse; `approved` is never withdrawn; `vote_yes_share` is 0 when there is no shared part. Validation keeps `vote_threshold` in `(0, 1]` (`params.py:121`), so a threshold of 0 (which would pass an empty vote) is REFUTED; the manifest minimum is 0.5. A threshold of 1.0 needs every floor-area share: passes only when all units are supporters, tested at `yes + 1e-9 >= 1.0` (a sum of areas divided by the total can land at 1 - 1e-16, which the 1e-9 tolerance absorbs; covered by edge fuzz).

Reachable questionable states (characterised, `repro/test_vote_characterisation.py`, SM-5 and SM-6):
* **SM-5, support reached but never passes**: one owner who cannot finance the share blocks the vote for ever and the only signal is `units_cannot_front` in the frame. Output of `pytest ... test_vote_characterisation.py -s`: `SM-5: 108 buildings pending at t=180 with support >= threshold, e.g. (case, building, yes_share, units_cannot_front) = [(5, 'f5', 0.629, 4), (15, 'b0', 0.646, 1), (18, 'b24', 1.0, 2)]`.
* **SM-6, charged past one's own horizon**: the vote pays for every owner without looking at NPV, including one whose stay has ended: `SM-6: 1 shared payments by households past their own horizon, e.g. (case, unit, month, horizon) = [(138, 44, 73, 64)]`.
Both are model-design questions (whether a vote binds a non-beneficiary); they are not claimed as defects here.

## 6. Machine M5: household decision and financing

Identity: `_evaluate` (`model.py:198-215`) and `_pay` (`217-248`); `plan_financing` and `loan_payment` (`financing.py:14-30`), `credit_limit` (`credit.py:7-20`), `npv_retrofit` (`npv.py:23-43`). Implicit; the "state" is the outcome of each evaluation.

Outcomes of `_evaluate(u, base)`:

| Outcome | Condition | Variables |
|---|---|---|
| not needing financing | quote `requires_financing` False (passthrough or public service, eligible) | `from_savings = loan = 0`, the state pays `price` |
| financed from savings | `upfront <= usable savings` | `from_savings = upfront`, `loan = 0` |
| financed with a loan, credit granted | `loan <= credit_limit + 1e-9` | `loan > 0`, `u.loans` gets `(payment, t + loan_term)` |
| credit refused | `loan > credit_limit + 1e-9` (limit 0 for `none`, or `income_tested` below the threshold) | `_evaluate` returns None: no candidate, no support, a blocked vote |
| rebate pending | `quote.rebate > 0` | entry in `pending[t + lag]` (M6) |
| rebate paid | month `t + lag` reached | `public_cost += rebate`, `cash_net += rebate` |

Candidate rule: the NPV must be positive for a household to act (`model.py:367`); the vote ignores it (SM-6).

Invariants (checked on every event, 8000 runs): `from_savings + loan + state_pays_now == price`; `from_savings <= savings at adoption`; `loan <= credit_limit` (1e-6 tolerance); `0 <= rebate <= price`; non-refundable `rebate <= tax_payable` and cumulative per household `<= tax` (`tax_left` accounting, line 231); `credit_access: none` gives `loan == 0` (limit 0 at `credit.py:15`); `price >= base_cost`; the subsidy never reaches a quintile above `means_test_max_quintile`.

Edge facts (attacked, held): `loan_payment` with rate 0 uses `principal / months` (`financing.py:27`); `loan_term_months` 1 and 1200 ran clean; `savings_scale` 0 with passthrough or public service still adopts (no financing needed); `credit_access: none` with passthrough adopts normally; `savings_usable_share` 0 forces everything onto credit. `rebate_per_euro` stays within `[0, 1]`.

Reachable invalid state: none inside the manifest region; NaN/inf parameters (SM-2).

## 7. Machine M6: rebate lag queue

Identity: `pending` dict `model.py:132`, push `222`, pop `335`; JS `Map` at `runtime.js:375, 449, 556`. Implicit; `rebate_arrival_month` in `rebate.py:18` is defined and never used by the model (the arrival month is recomputed inline).
State: for each future month, a list of `(unit id, cash)`.

| From | Event | Guard | To | Side effects | Lines |
|---|---|---|---|---|---|
| (none) | `_pay` with `rebate > 0` | | queued at `t + lag` | event logged with the entitlement | 221-222 |
| queued at m | `step` with `t == m` | phase 1 | delivered | `public_cost += cash`, `cash_net += cash` | 335-337 |
| queued at m <= t of the push | | | **never delivered** | stays in `pending` for ever | SM-1 |

Invariants: every entry has `month >= t` (checked by `sim_problems` after each step), `uid` valid, `cash > 0`; `public_cost` equals vendor payments plus rebates whose month is within the executed steps (`fuzz_lib.event_problems`, exact to 1e-9 relative on all manifest cases with lag >= 1). Rebates due after the last executed step stay queued; that is the end of the run, not a defect.

### SM-1 (CONFIRMED): lag 0 rebate is queued for a month already processed

Cause: within month `t`, phase 1 pops `pending[t]` (line 335) before phase 4 pushes `pending[t + 0]` (line 222). `rebate_lag_months` is validated as `>= 0` (`params.py:105`) and the manifest allows `min: 0` (`pack.yaml:18`). The same code is in `runtime.js:448,556`.
A fractional lag (Python API, e.g. 1.5) is accepted and its key `t + 1.5` is never an integer step, so it is lost in the same way (`repro/test_params_nonfinite.py::test_fractional_rebate_lag_is_rejected`).

Repro, Python:

```
$ PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_rebate_lag.py -q -rx
xx.   (3 tests: lag 0 public cost, stranded queue, control with lag 1)
XFAIL ...test_lag_zero_rebate_reaches_public_cost - SM-1: lag 0 rebates are queued under the current month ...
XFAIL ...test_no_rebate_stranded_in_the_queue - SM-1: the rebate queue keeps entries whose month is in the past
```

Probe behind it (30 buildings, 60 months, `credit_access=open`, `deduction_rate=0.5`): lag 0 entitles 250,018 euros of rebate and `public_cost` at t = 60 is 0; lag 1 entitles the same 250,018 and `public_cost` is 250,018. The fuzz white-box check flags 186 of 300 lag-0 cases ("rebate queue holds 1 item(s) due in month 14, already past (t=15): never delivered").
Repro, JS:

```
$ node docs/state-machines/repro/js/lag_zero.js
lag 0 rebate entitled 250018 public_cost at t=60 0
BUG PRESENT
lag 1 rebate entitled 250018 public_cost at t=60 250018
```

Impact: with lag 0 every rebate-mode result silently loses its rebate: `public_cost`, `net_cash_by_quintile` and everything derived. The adoption decision still counts the rebate (`npv.py:41` uses it), so households act on money that never arrives in the accounts. Likelihood: high, the slider reaches 0. The numbers above are placeholders, only the mismatch matters.

## 8. Machine M7: public-service capacity queue

Identity: `model.py:374-381` (phase 4) and 391-395, 407-408 (phase 5); `quota` and `carry` at lines 144-145; JS `runtime.js:593-602, 610-613`. Explicit-ish: `carry` carries the fractional slot.
State: `quota = public_capacity * n_units / 12`, `carry in [0, 1)`, `slots = int(quota + carry)` per month, `allowed` (the first `slots` candidates by `(queue_draw, uid)`), `slots_left`.

| From | Event | Guard | To | Side effects | Lines |
|---|---|---|---|---|---|
| month start | step in `public_service` mode | | `slots = int(quota + carry)` | `carry = quota + carry - slots` | 375-377 |
| candidates | rank | `capacity_limited` quotes only (eligible households; market fallback households are never limited) | `allowed` = first `slots` | the rest wait, they re-roll their consideration next month | 378-380 |
| after phase 4 | | | `slots_left = slots - len(allowed)` | | 381 |
| vote ready | | `ceil(units*shared_share - 1e-9) <= slots_left` | approved | `slots_left -= need`, `VoteEvent.slots_used = need` | 391-409 |

Invariants (exact, no slack, 8000 runs): per month, subsidised unit/whole jobs plus the `slots_used` of votes are `<= int(quota + carry)` recomputed independently; `0 <= carry < 1`; `public_capacity: 0` gives 0 subsidised jobs; `public_capacity: 1` is accepted. REFUTED defects: capacity exceeded (R-4). Unused whole slots are lost (only the fraction carries), which is a modelling choice.

Observation (not a defect): shared work is charged to every owner even if some of them are outside a means test and buy on the market (their quote is not capacity limited), while `need` counts all `units`. A vote in a mixed building therefore reserves more slots than the public share of the work. Also `quota` is over all dwellings including rental ones (`len(self.units)`), as the parameter text says.

## 9. Machine M8: means test and eligibility

Identity: `_eligible` `delivery.py:37-39`, `_market_quote` 42-46; JS `runtime.js:142-147`. Implicit.
States of a household for a quote: in scheme (quintile <= `means_test_max_quintile` or no means test) or market fallback.
The fallback is applied in all three modes, including `rebate_market` (`delivery.py:54`), as model-spec 7.3 says; `pack.yaml:31` says the opposite: **SM-4 (CONFIRMED)**.

```
$ PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_means_test_help_text.py -q -rx
.x
XFAIL ...test_help_text_matches_behaviour - SM-4: user-facing help text contradicts the behaviour above
```

The passing test next to it pins the behaviour: with `means_test` on and `rebate_market`, every event with a rebate has quintile <= 2, and market purchases by quintiles 3 to 5 carry no rebate and `subsidised == False`. Fixing the text (or the behaviour, as the project decides) flips the strict xfail. Impact: a policymaker reads that the rebate is untouched by the means test.

## 10. Machine M9: canvassing time budget

Identity: `_spend` `model.py:191-196`, pressure at 361, population hours 108-111 (JS `runtime.js:417-421, 580, 342-346`). Implicit.
State per household: `free_hours = max(0, base * spread)`, advocate (`supporter or paid_any`) and co-owned building; weekly canvassing `spend = min(free_hours, canvass_target_hours)`; building pressure `min(1, (sum of others' spend) / canvass_saturation_hours)`, entering only the consideration probability of condos (`ownership.py:48`).
Invariants (checked): `leisure_hours = free_hours - spend >= 0`, `canvass_hours >= 0`; probability clipped to 1 (`min(1.0, ...)`, `ownership.py:48`); `canvass_target_hours` 0 and 10 and `canvass_saturation_hours` 1e-6 and 1e6 held. A household's own spend is excluded from its pressure (line 361), so a lone advocate gets none.
Reachable invalid state: `waking_hours_per_week = inf` or `saving_per_m2_year = inf` gives inf in `leisure_hours`/`bills_saved` (SM-2; not reachable from sliders).

## 11. Machine M10 and M11: energy scenarios; scene entities; params

**Energy scenarios** (`params.py:22,137-139`, `model.py:338`, `npv.py:5-20`): stateless. `level = (1 + g_m)^t` with `g_m` from the scenario; `annuity_pv` has a special case when `|q - 1| < 1e-12` (`npv.py:18`). Validation restricts the scenario to `flat | rising | shock`; the three growth rates are only validated as floats in the Python signature, with no range check (`params.py` has no check for `energy_growth_*`; `-1` or below would make `(1+g)` non-positive; not reachable from the manifest, listed under SM-2 class). `monthly_rate(annual <= -1)` would give a complex number in Python and NaN in JS: SUSPECTED, not repro'd because no manifest or `Params` path sets it except an explicit `energy_growth_rising=-2.0`; that call is accepted by the validator.

**Scene entities** (`scene_entities.py:41-66`, `runtime.js:193-217`, bind.js `78-110`): a pure function from rows to buildings.

| Step | Rule | Lines |
|---|---|---|
| exclude | `not residential` -> `non_residential`; `area <= 0` or `storeys <= 0` -> `invalid_geometry` (NaN is caught by `!(area > 0)` in JS but `area <= 0` is False for NaN in Python, which then raises on `round(nan)`: SUSPECTED, Python rows only come from `synthetic_table`) | py 45-51; js 200-202 |
| units | `max(1, round(gross / avg_unit_area))`, half-to-even in both (`pyRound`) | py 53; js 204 |
| tenure | `draw < rental_share` -> rental, else owner-occupied (1 unit) or condo | py 54-59 |
| areas | deterministic spread, total preserved | py 61-65 |

Invariants: at least one unit with positive area per building, total area equals `gross` (checked by `v3/test_v3/test_entities.py`; parity checked on every fuzz case through `synthetic_table`). No upper bound on units (SM-9 consequence). `bind.js` guards: area from the footprint polygon if `area` is not positive, storeys from levels, height/3 or 1.

Defects here: **SM-7**, **SM-8**, **SM-9**.

### SM-7 (CONFIRMED): scene with no residential building

`bindScene` returns count 0 (`bind.js:106`). In `paramsFromPack`, `else if (b && b.count) o.n_buildings = b.count` (`runtime.js:688`) is False for 0, so the Params default `n_buildings: 200` is used and 200 synthetic buildings run against a declared entity count of 0.

```
$ node docs/state-machines/repro/js/zero_residential_scene.js
bindScene -> {"building":0}
BUG PRESENT: start() throws: runtime great-retrofit, frame 0: entities.building.state has 200 values, expected 0; entities.building.tenure has 200 values, expected 0; ...
with validation off: frame carries 200 buildings for a declared count of 0
```

### SM-8 (CONFIRMED): buildings without an id

```
$ node docs/state-machines/repro/js/idless_buildings.js
entities {"building":3} scene index of each entity [ -1, -1, 2 ] warnings ["2 building entities name a building the scene does not have (undefined, undefined): not drawn"]
BUG PRESENT: 2 modelled building(s) stand on no scene building
```

Cause: `rows.push({ id: b.id, ... })` (`bind.js:98`) then `String(row.id)` = `"undefined"` (`runtime.js:199`); paperdolls looks them up as `"#0"`, `"#1"` (`packruntime.js:54`). They still count in every series.

### SM-9 (CONFIRMED): Int16 overflow of `units`

```
$ node docs/state-machines/repro/js/int16_overflow.js
model units in the building: 40000
frame units field: -25536  units_done: 0
BUG PRESENT: units wrapped
```

(`runtime.js:651`; also `units_done`; `cannot_front`'s `Int8Array` is fine as it holds 0/1 and the category arrays hold small indices.)

### Params validation (M12)

`Params.__post_init__` (`params.py:101-135`) and the JS `Params()` (`runtime.js:290-312`) are the same list. Python-vs-JS acceptance was compared value by value (`tests/fuzz/run_js_params.js`) over every field and 18 values each. Differences, by cause:

| Cause | Python | JS | Status |
|---|---|---|---|
| NaN in `validate_positive/nonnegative` | accepts (comparison False) | rejects (`!(v > 0)`) | SM-2 CONFIRMED |
| `null`, `"0.5"`, `[]` where a number is expected | `TypeError` | accepted, coerced (`null >= 0`) | SM-10 CONFIRMED |
| float with integer value (1.0, 3.0, 1e308) for integer fields | `ValueError` | accepted (`Number.isInteger`) | harmless: JS has one number type; `1e308` months would hang a run, not reachable from sliders |
| `True` for integer fields | accepted (bool is int) | rejected | harmless |
| inf | accepted where `>= 0`/`> 0` | accepted | SM-2 |
| manifest range edges (min, max, default of every numeric param) | accepted | accepted | REFUTED as a defect (`test_validator_parity_on_manifest_ranges`) |

Gaps in both: no check on `energy_growth_*`, `income_log_mean`, `rebate_lag_months` integrality (SM-1 fractional), `scene_rules` ranges beyond probability checks, explicit buildings (SM-3), `seed` type. Every min, max and default of the manifest ranges is accepted by both validators.

## 12. Frame invariants (the checks the fuzz applies at every step)

`fuzz_lib.frame_problems`, `sim_problems`, `event_problems`:

1. schema is 1, `year == t / 12`, `len(frame.buildings)` equals the scene size, ids keep their order.
2. every number is finite (null only in the four nullable series).
3. state counts sum to the number of buildings and match a recount; tenure counts sum; `shared_counts` match the buildings.
4. `adopted_share` in `[0,1]`, `adopted_share * units` integer, state follows the count; rental inert; `units_cannot_front` in `[0, units - adopted]`; `income_q_mean` in `[1,5]`; `vote_yes_share` in `[0,1]` and 0 without shared parts.
5. `adopted_units` equals the sum over buildings and never exceeds the units of modelled buildings; monotone: `adopted_units`, `public_cost`, `bills_saved`, each building's `adopted_share`, and approvals never decrease.
6. five values in each per-quintile series; shares in `[0,1]`; `rebate_per_euro` in `[0,1]`; hours non-negative.
7. `cost_per_retrofit` and `cost_per_retrofit_parts` are null exactly when `adopted_units == 0`; otherwise `base + markup == cost_per_retrofit` (to 1e-9 relative) with `markup >= 0`.
8. white-box (live `Simulation`): savings >= 0, `0 <= tax_left <= tax`, counters in step, queue entries not in the past, `0 <= carry < 1`.
9. event log: payers add up to the price, savings not overdrawn, loan <= credit limit, rebate <= price and (non-refundable) <= tax payable, no subsidy beyond the means test, a vote never passes below threshold, public-service jobs <= slots each month, `public_cost` = vendor payments + arrived rebates.

Result: all hold on 8000 runs (see section 1), with the single exception of item 8's queue entry check and item 9's last line under lag 0 (SM-1), and the validation gaps of M12.

## 13. Machine M13: runtime handle lifecycle

Identity: the registered runtime `runtime.js:692-707` (`init`, `step`, `run`; plus `bindScene` added by `hook.js:22-27`), wrapped by `PackRuntime.create` (`packruntime.js:146-192`). Explicit in `docs/pack-spec.md` ("Runtime interface"), partly implicit in the adapter's closure variables `handle`, `t`, `params`, `seed`.

Interface actually provided (`lifecycle_surface.js`): `init, step, run, bindScene`. **Absent: `setParams`, `snapshot`, `restore`, `inspect`.** `pack.yaml:10` says `on_params: rerun`, so `setParams` is not required; `canSnapshot` and `canInspect` are false. If the manifest were switched to `continue`, `PackRuntime.create` refuses: `on_params: continue -> runtime great-retrofit: setParams is missing (runtime.on_params is "continue")` (SM-11, a documented limitation, not a defect).

States: **UNINIT** (no handle) -> **READY** (`t = 0`, after `start`) -> **RUNNING** (`0 < t < 180`) -> **AT_END** (`t = manifest time.steps = 180`) -> **PAST_END** (`t > 180`).

| From | Event | Guard / behaviour | To | Lines |
|---|---|---|---|---|
| any | `start(p, seed)` | `Object.assign` copies, `impl.init`, then `impl.step(h, 0)` must be frame 0 | READY (`t = 0`), previous handle dropped | pr 165-169; rt 694 |
| UNINIT | `step`, `run` | throws "start() first" | UNINIT | pr 177-179 |
| any | `setParams(p)` with `rerun` | calls `start(p)`; keeps the **previous seed** (no seed argument) | READY | pr 171-173 |
| READY..RUNNING | `step(n)` | `n = max(0, n|0)`; `impl.step(h, n)`; frame i must have `t == t0 + i + 1` | RUNNING/AT_END | pr 177; rt 695-700 |
| READY..RUNNING | `run(T)` | `T = min(horizon, T|0)`; returns `[]` if `T <= t`; else `impl.run` | RUNNING/AT_END | pr 178-183; rt 701-704 |
| AT_END | `run(T)` again | `T <= t` returns `[]` (checked: `run(180)` then `run(180)` gives 180 then 0 frames) | AT_END | pr 180 |
| AT_END | `step(n)` | **not clamped**: the runtime keeps simulating; frame 181 is returned and validates (SM-12) | PAST_END | pr 177, rt 695 |
| any | `step(0)` after start | wrapper expects frame `t + 1`, runtime returns the current frame: throws "t is N, expected N+1" (SM-13, paperdolls) | unchanged | pr 177 |
| any | `snapshot`, `restore`, `inspect` | missing in this runtime; wrapper throws `this runtime has no snapshot` or returns null | | pr 184-189 |

Variable encoding: handle `{ sim }` holds every piece of state in `Simulation`'s own fields; `Params` is frozen; module-level state is only constants and strategy objects, so two handles never share mutable state (REFUTED: shared state, R-8).

Invariants and checks:
* `frame.t == index` for every frame (adapter check).
* every array has the declared count: the count is fixed when `create()` is called (`ents`, `counts`) and **cannot change on `setParams`**, but `paramsFromPack` takes `n_buildings` from the count only when `b.count` is truthy (SM-7).
* determinism: same `(params, seed)` gives identical frames, regardless of chunking (`step(1)` x n, `step(n)`, `run(n)`) and of interleaving with a second handle (lifecycle fuzz, 40 programs: 0 problems).
* `setParams` under `rerun` is equal to a fresh `start` with the same seed (checked); with a different seed in the program it is not, because the adapter keeps the last seed (that is the contract, noted so nobody expects the new `seed`).
* inputs are not mutated by `init`/`step` (`probe`: specs and params byte-identical after 24 steps).
* emulated snapshot: `structuredClone` of the `Simulation`'s own fields (`mode` rebuilt from `p.delivery_mode`, because `mode` holds functions and is the one field a naive clone throws on) continues exactly as the original, and a clone of a clone has the same `t`. So a future `snapshot`/`restore` can be a plain clone plus `mode` rebuild; nothing is hidden in closures.

Hazard if `continue` is ever implemented (SUSPECTED, design note, no repro possible because the entry points do not exist): `Simulation` derives these from `Params` once in the constructor and stores them: `mode`, `rM`, `gM`, `needsShared`, `quota`, per-unit `unit_base`/`shared_base`, the population itself (income, savings, horizon, `queue_draw`, quintile, free hours) and the tenure from `_retenure`. A `setParams` that only swapped `sim.p` would leave those stale (for instance a new `delivery_mode` would still use the old `mode`; a new `public_capacity` the old `quota`; queued rebates keep their old lag). It would have to rebuild or document which levers apply "from now on".

Other lifecycle facts:
* **SM-12 (SUSPECTED impact, behaviour CONFIRMED by `lifecycle_surface.js`)**: nothing in the runtime knows the manifest horizon; `step` past 180 yields frame 181, 182 ... and `PackRuntime.run` clamps while `PackRuntime.step` does not. What the store does with frame 181 was not tested (paperdolls out of scope); the Python `Simulation` is unbounded in the same way, `run_simulation` bounds it by `horizon_months`.
* `run(h, Infinity)` or a huge `toT` called on the bare impl would loop for ever (`while (h.sim.t < toT)`, `runtime.js:703`); REFUTED through the adapter (`toT = Math.min(horizon, toT|0)`), not tried on the bare impl because the run would not return.
* `seed | 0` (`runtime.js:685`): seeds above 2^31 wrap to negative 32-bit values; Python masks to 32 bits too. Python and JS agree on seeds 2^31, 3e9, 2^32-1, 2^32+5, 2^40+7 (edge fuzz). Fractional seeds are truncated; NaN becomes 0.
* `hook.js` must load before `runtime.js` (it wraps `registerRuntime`); if loaded after, the runtime registers without `bindScene` and the pack falls back to the invented placement without a warning (SUSPECTED from `hook.js:12-14`; the bundle order is fixed by `tools/bundle.js`, so not reachable there). The scene seed is hard-coded to 1 in `hook.js:25`.
* `PackRuntime.setParams` under `rerun` returns the new frame 0; any stale `run` in flight is the worker's business (PackWorker not exercised here).

## 14. Attacked and refuted

| ID | Claim | Why it cannot happen | Line / evidence |
|---|---|---|---|
| R-1 | adopted units exceed units | counters only increase on `complete` once per unit | `model.py:241-248`; 8000 runs |
| R-2 | a retrofit is undone | `complete`, `unit_done`, `shared_paid`, `approved` are never reset | no assignment of False after init |
| R-3 | negative budget (savings, tax, shares) | `from_savings <= min(usable, upfront)`; `tax_left` clamped | `financing.py:17-18`, `model.py:231` |
| R-4 | public service above capacity | slots recomputed independently, no slack, 8000 runs; capacity 0 gives 0 jobs | M7 |
| R-5 | rebate above cost or above tax payable | `min(gross, max(0, tax), cost)` | `rebate.py:15` |
| R-6 | cost-per-retrofit series is not the sum of its parts | `base + markup == price_sum / n` to 1e-9 relative; both null together | `model.py:317, 322`, check 7 |
| R-7 | NaN in a frame inside the manifest region | all means guarded by counts; the only NaN is the adapter's `nz(null)` | `runtime.js:646`, checks 2 and 6 |
| R-8 | handles share state | module level holds constants and stateless strategies | `runtime.js` header; interleaved handles checked |
| R-9 | vote threshold 0 passes an empty vote | `0 < t <= 1` validated in both | `params.py:121`, `runtime.js:302` |
| R-10 | zero buildings or zero units from Python's own scene path | `n_buildings` positive; `build_entities` makes `>= 1` unit; zero buildings only arises from the scene (SM-7) | `params.py:103`, `scene_entities.py:53` |
| R-11 | one building, all-rental scene, zero units adopted | all frames valid and finite (state `not_modelled`, series null where they should be) | edge fuzz |
| R-12 | `NaN`, `inf`, `-0` from empty denominators in frames | each division guarded (`if n else None`, `if self.q_total[k] else`) | `model.py:317-330` |
| R-13 | JS-Python drift beyond tolerance | 8000 cases, 0 differences | section 15 |

## 15. Python vs JavaScript

Mechanisms that keep them equal and could silently stop doing so:

* `pyRound` (half to even) for unit counts and household horizons (`runtime.js:32-37`, `204`, `330`, `654`); `Math.round` would disagree on exact halves.
* `pySum` (Neumaier compensation, CPython 3.12 `sum`) for `s = sum(raw)` in scene areas (`runtime.js:213`, `scene_entities.py:63`). **SUSPECTED** to differ on Python 3.10 and 3.11 (`pyproject.toml` allows >= 3.10; their `sum()` is plain): at most last-bit differences in unit areas, inside the 1e-9 tolerance but able to flip an NPV sign at the margin. Blocked: only Python 3.12.3 is installed here.
* Plain loops in unit order for every other sum (`model.py` docstring).
* `Math.pow` vs `**` and `exp/log/cos`: parity held at 1e-9 on 8000 cases, including discount rates 0, 1 and 0.3 and loan terms up to 1200 months; no divergence found.
* Error types differ (Python `ValueError/TypeError/KeyError/ZeroDivisionError`, JS `Error/TypeError`); only acceptance matters (table in M12).

Fuzz evidence: `test_fuzz_parity.py` compares the whole frame tree (every building and series, every step), events and votes, tolerance 1e-9 relative, and checks the adapter's typed arrays against an independent re-derivation. Zero differences, which includes the edge region (vote threshold 1.0, shared share 0 and 1, consideration probability 0 and 1, credit none with passthrough, capacity 0 and 1, all-rental scenes, one-building scenes, big condos, seeds beyond int32).

Same bug on both sides (the golden tests agree with it): SM-1 (`runtime.js:448, 556`) and SM-4.

## 16. No-data and NaN handling in frames

* Python frames use `None` for no-data in `rebate_per_euro`, `can_front_cost`, `cost_per_retrofit`, `cost_per_retrofit_parts`, `net_cash_by_quintile` (schema, `frames.py`).
* The adapter turns them into `NaN` (`nz`, `runtime.js:646`), and `cost_parts` into `[NaN, NaN]`; categories use indices and never `-1`; everything else is finite. `rental_share` is 0 when there are no buildings (guarded, `runtime.js:677`).
* The shell's `checkFrame` accepts NaN as a number (`typeof NaN === 'number'`), so a model that leaks NaN elsewhere would not be caught by it; the fuzz scans every number for finiteness instead (check 2).
* **SM-15 (characterisation)**: per-quintile series that are not nullable (`adoption_by_quintile`, `canvass_hours`, `leisure_hours`) report 0.0 for a quintile with no household (fewer than 5 dwellings; `model.py:107` gives quintile `1 + rank*5//n`), where `can_front_cost` says no data. With two single-dwelling buildings: `adoption_by_quintile [0.0, 0.0, 1.0, 0.0, 0.0]`, `leisure_hours_by_quintile [15.36, 0.0, 31.34, 0.0, 0.0]`, `can_front_cost [0.0, None, None, None, None]`. Irrelevant for a scene of hundreds of dwellings; matters for small scenes and for any per-group chart that reads 0 as "nobody adopted".
* Non-finite inputs reach the frames only through SM-2.

## 17. Open items and what blocked them

* SM-12: effect of frame 181 on the store: needs the paperdolls store/worker, out of scope.
* Python < 3.12 parity (`pySum`): no interpreter available here.
* `monthly_rate` with an annual rate <= -1 (explicit `energy_growth_*` below -1): validator accepts it; not exercised.
* Python `build_entities` with NaN `area`: only reachable with rows that do not come from `synthetic_table`.
* PackWorker (structured clone of frames, cancellation of an in-flight `run` by `setParams`): not driven.
