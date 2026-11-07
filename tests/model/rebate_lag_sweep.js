/* Rebate lag sweep (SM-1) in the JS port. Prints, for lag 0..24 and the given fractional lags, the same numbers as test_rebate_lag.py's python_sweep(). */
'use strict';
const path = require('path');
const GR = require(path.join(__dirname, '../../packs/great-retrofit/runtime.js'));
const CFG = { n_buildings: 30, horizon_months: 120, credit_access: 'open', deduction_rate: 0.5, saving_per_m2_year: 200, delivery_mode: 'rebate_market', seed: 3 };
function one(lag) {
  const sim = new GR.Simulation(GR.Params(Object.assign({}, CFG, { rebate_lag_months: lag })));
  for (let i = 0; i < CFG.horizon_months; i++) sim.step();
  const pend = [...sim.pending.entries()].filter(([m]) => m < sim.t).length;
  let cash = 0; for (const u of sim.units) cash += u.cash_net;
  const queued = [...sim.pending.values()].reduce((a, v) => a + v.reduce((s, x) => s + x[1], 0), 0);
  return {
    lag, effective_lag: sim.p.rebate_lag_months, n_events: sim.events.length, entitled: sim.events.reduce((a, e) => a + e.rebate, 0),
    public_cost: sim.frame.series.public_cost, cash_total: cash, queued, stale_keys: pend,
    event_keys: sim.events.map(e => [e.month, e.unit]),
    net_cash: sim.frame.series.net_cash_by_quintile,
  };
}
const lags = JSON.parse(process.argv[2] || '[]');
console.log(JSON.stringify(lags.map(one)));
