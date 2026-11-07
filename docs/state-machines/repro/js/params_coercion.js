/* SM-10: JS Params() uses JS comparisons (null >= 0, "0.5" > 0, [] >= 0 are true), so values Python rejects are accepted and coerced. Exit 1 while present. */
const E = require('../../../../tests/fuzz/lib/pack_env.js'); const { GR } = E.load();
let bad = 0;
for (const [name, v] of [['deduction_rate', null], ['deduction_rate', '0.5'], ['cost_per_m2', '300'], ['loan_rate', []], ['canvass_target_hours', null]]) {
  try { GR.Params({ [name]: v }); console.log('accepted', name, '=', JSON.stringify(v)); bad++; } catch (e) { console.log('rejected', name, JSON.stringify(v)); }
}
if (bad) { console.log('BUG PRESENT:', bad, 'non-numeric values accepted'); process.exit(1); }
