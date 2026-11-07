/* SM-4 in the JS port: with the means test on, the rebate is restricted too. Prints the counts test_means_test_scope.py compares. */
'use strict';
const path = require('path');
const GR = require(path.join(__dirname, '../../packs/great-retrofit/runtime.js'));
const r = GR.runSimulation(GR.Params({ n_buildings: 60, horizon_months: 84, credit_access: 'open', deduction_rate: 0.5, delivery_mode: 'rebate_market', means_test: true, means_test_max_quintile: 2, savings_scale: 3.0 }));
const ev = r.events;
console.log(JSON.stringify({
  n: ev.length,
  rebate_above_cut: ev.filter(e => e.quintile > 2 && e.rebate > 0).length,
  rebate_inside: ev.filter(e => e.quintile <= 2 && e.rebate > 0).length,
  market_above_cut: ev.filter(e => e.quintile > 2 && !e.subsidised && e.rebate === 0).length,
  subsidised_above_cut: ev.filter(e => e.quintile > 2 && e.subsidised).length,
}));
