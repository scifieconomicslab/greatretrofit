/* SM-10 regression (issue #4): JS Params() used to coerce (null >= 0, "0.5" > 0, [] >= 0 are true) and accept values Python rejects. Exit 1 if any is accepted again. */
const E = require('../fuzz/lib/pack_env.js'); const { GR } = E.load();
let bad = 0;
for (const [name, v] of [['deduction_rate', null], ['deduction_rate', '0.5'], ['cost_per_m2', '300'], ['loan_rate', []], ['canvass_target_hours', null], ['refundable', 1], ['seed', '3'], ['work_hours_by_quintile', ['40', 40, 40, 40, 40]]]) {
  try { GR.Params({ [name]: v }); console.log('ACCEPTED', name, '=', JSON.stringify(v)); bad++; } catch (e) { console.log('rejected', name, JSON.stringify(v), '-', e.message); }
}
GR.Params({ deduction_rate: 0.5, cost_per_m2: 300 });       // real numbers still pass
if (bad) { console.log('BUG PRESENT:', bad, 'non-numeric values accepted'); process.exit(1); }
