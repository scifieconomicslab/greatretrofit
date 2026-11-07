# Design questions behind three pinned behaviours (SM-5, SM-6, SM-15)

These three behaviours are not confirmed bugs. The code does what it was written to do, and a characterisation test pins each one so that a change cannot happen by accident. They are questions about what the model is supposed to say, so each needs a decision from the modelling team (tracked in issue #5). **Nothing here changes behaviour**, and every number below comes from a placeholder run: it shows how often a code path is taken, it is not a result about households or policy.

How the numbers were produced: the 200 sampled 180-month runs are `fuzz_lib.case_for("manifest", seed)` for seeds 0 to 199 with `horizon_months=180` and `shared_measure=True` (6,060 dwellings in total, 746 buildings with shared parts), the same sample as `docs/state-machines/repro/test_vote_characterisation.py`. Rerun with:

```bash
PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_vote_characterisation.py docs/state-machines/repro/test_nodata_characterisation.py -q -s
```

| Decision | Pinned by | Code | Issue |
|---|---|---|---|
| D1 (SM-5): a vote that has the support but cannot be paid by one owner | `test_vote_can_be_stuck_pending_with_enough_support` | `model.py` phase 5 (`_evaluate` returns None for an owner, `continue`); `runtime.js` step 5 | #5 |
| D2 (SM-6): a household charged for the shared part after its own horizon | `test_shared_share_is_charged_after_the_payers_own_horizon` | `model.py` phase 5 (`_pay(kind="shared")` for every owner, no NPV or horizon test) | #5 |
| D3 (SM-15): an empty quintile drawn as 0 instead of no-data | `test_empty_quintiles_read_as_zero_not_no_data` | `model.py` `_make_frame` series (`if self.q_total[k] else 0.0`); `runtime.js` `toPackFrame` | #5 |

## D1. A vote reaches the threshold but never passes (SM-5)

**What happens today.** A condo building's shared part (windows, facade, roof) is voted on by floor-area share. Once the share of supporters reaches `vote_threshold`, the vote still passes only if every owner can pay their floor-area share of the shared cost, from savings plus credit (`_evaluate(...)` is not None for all). If one owner cannot, the vote does not pass this month and is retried every month. Nobody's circumstances change except through other purchases, so in practice it stays blocked. The only trace in the frame is `units_cannot_front` for the building, and `shared_state` stays `pending`.

**Numbers (200 runs, 180 months, placeholder parameters).**

* 108 of the 475 buildings that are `pending` at month 180 have support at or above the threshold. They are in 43 of the 200 runs and hold 524 dwellings.
* In those buildings 187 dwellings have already paid their own part and wait for the vote, so they never become `retrofitted`. For comparison 1,146 of 6,060 dwellings are complete at month 180.
* The shared base cost of the 108 buildings is about 4.97 million euros (placeholder costs). 30 owners cannot front their share of it, about 0.29 million euros.
* The quintiles of the 30 owners who cannot pay, by income quintile 1 to 5: 1, 2, 12, 9, 6. This is how the placeholder credit rule and savings distribution fall out in this sample; it is not a finding about who is left behind.

**Options.**

| Option | What it means | What changes in the series |
|---|---|---|
| A. Stay blocked (today) | One owner who cannot pay holds the whole building back. It is the model's story about who is left behind. | Nothing. `shared_by_state` keeps a pending count, `units_cannot_front` and `can_front_cost` carry the signal. |
| B. Credit covers it | The vote passes and the owner's share is financed by a loan beyond their normal credit limit (or the limit is waived for shared parts). | More buildings approved and more `retrofitted` (up to the 187 waiting dwellings in this sample become complete at once); `adopted_units`, `adoption_by_quintile` and `cost_per_retrofit` rise; the owner's loan payments appear in `net_cash_by_quintile`; `public_cost` is unchanged in rebate mode and rises in pass-through and public service. The credit lever stops limiting shared parts, so `credit_access: none` would no longer block them. |
| C. The others cover it | The vote passes, the other owners pay the missing share (cross-subsidy inside the building). | Same approvals as B, but the cost moves to the other owners: higher `cost_per_retrofit` for them, lower `net_cash_by_quintile` for the quintiles that pay, and a transfer from one quintile to others that the model does not show today. Needs a rule for how the missing share is split. |
| D. Public money covers it | The state pays the missing share. | Same approvals; `public_cost` rises by about the 0.29 million of the sample; a new transfer to be named in the frame. |

**What the decision needs.** Which of the four tells the story the pack should tell. B, C and D each remove a mechanism that currently keeps some households out, so they also change what the credit and means-test levers appear to do. If the answer is A, the test is renamed from "pins current behaviour" to "asserts intended behaviour" and the frame could gain a plain "blocked by one owner" count.

## D2. A household is charged for the shared part after its own horizon (SM-6)

**What happens today.** The household decision uses the stay horizon (`u.horizon`): after it, a household never considers a retrofit again and, in the NPV, its savings stop. The vote does not look at NPV or horizon: when a building's vote passes every owner pays their share, including an owner whose expected stay has already ended (and who, by the model's own rule, would not buy). The payment is booked as an ordinary event, counted in `public_cost` or the household's cash, and counts toward the dwelling being complete.

**Numbers (same 200 runs).** 1 shared payment in the whole sample is made past the payer's horizon: case 138, unit 44, month 73 against a horizon of month 64, quintile 4, price 10,013 euros (placeholder). It is rare here because most votes pass early; how often it happens under other parameters was not measured.

**Options.**

| Option | What it means | What changes in the series |
|---|---|---|
| A. Charge everyone (today) | A vote binds every owner in the building, whatever their remaining stay (as a real owners' vote would). | Nothing. |
| B. Stop at the horizon | A household past its horizon is not charged and does not count as paid; the building cannot complete while one owner is past their horizon. | Fewer completions and `retrofitted` buildings; those buildings stay `partial` at the end (they already can: see state-machines.md, M2); `public_cost` and `net_cash_by_quintile` lose the late payments; needs a decision on who pays the missing share (see D1 options). |
| C. Household sells and leaves | At its horizon a household leaves and a new household moves in with a new horizon. | Larger change: a turnover model (new incomes, savings, horizons), `adoption_by_quintile` would count dwellings, not households, and events would need a household id. It is a different model, not a fix. |
| D. Charge, but exclude from NPV claims | Keep A but flag those payments in the event log so that charts of net cash do not read them as chosen purchases. | No change in totals; one extra field in events. |

**What the decision needs.** Whether the model is about owners' votes binding everyone (A or D) or only about the people who stay (B or C). The effect in the current sample is 1 payment, so the choice matters for the story, not for the size of today's series.

## D3. Empty quintiles are drawn as 0, not as no-data (SM-15)

**What happens today.** Households are split into income quintiles by rank (`quintile = 1 + rank * 5 // n`). With fewer than 5 dwellings some quintiles are empty. The nullable series (`can_front_cost`, `rebate_per_euro`, `net_cash_by_quintile`) say no data (`None` in Python, NaN in the pack frame). The series that are not nullable (`adoption_by_quintile`, `canvass_hours_by_quintile`, `leisure_hours_by_quintile`) report 0.0, which a chart reads as "nobody adopted" or "no leisure time".

**Numbers.** Two single-dwelling buildings (the test above): `adoption_by_quintile [0.0, 0.0, 1.0, 0.0, 0.0]`, `leisure_hours_by_quintile [15.36, 0.0, 31.34, 0.0, 0.0]`, `can_front_cost [0.0, None, None, None, None]`. A scene of hundreds of dwellings never has an empty quintile, so Jette is not affected; a very small or heavily filtered scene is.

**Options.**

| Option | What it means | What changes in the series |
|---|---|---|
| A. Keep 0 (today) | Empty quintiles read 0. | Nothing. |
| B. No-data for empty quintiles | The three series become nullable: `None` in Python, NaN in the pack frame, where an empty quintile has no household. | Frame schema change (three more nullable series in `frames.py`, `v3/docs/frame-schema.md`, `nz` in `runtime.js`), golden files regenerated for empty-quintile cases only, charts draw no point instead of 0. Python and JS must change together. |
| C. Require at least 5 dwellings | Reject or warn for scenes below 5 dwellings. | No series change; a new validation rule and message. |

**What the decision needs.** Probably B, which matches the three nullable series already there, but it is a schema change and the owner of the frame schema should confirm.

## After the decisions

For each decision made: change the code in Python and JS together, regenerate the golden files (`packs/great-retrofit/tools/regen_golden.py`) and explain the diff, rewrite the matching characterisation test from "pins current behaviour" to "asserts intended behaviour", update `docs/state-machines.md` and `v3/docs/model-spec.md`, and keep the fuzz and parity suites green. Until then all three behaviours stay as they are.
