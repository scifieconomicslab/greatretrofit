/* SM-1 in the JS port: rebate_lag_months = 0 (slider minimum) never delivers the rebate. Exit 1 while the bug is present. */
const E = require('../../../../tests/fuzz/lib/pack_env.js'); const { GR } = E.load();
const run = lag => GR.runSimulation(GR.Params({ n_buildings: 30, horizon_months: 60, credit_access: 'open', deduction_rate: 0.5, rebate_lag_months: lag }));
for (const lag of [0, 1]) {
  const r = run(lag), entitled = r.events.filter(e => e.month + lag <= 59).reduce((a, e) => a + e.rebate, 0);
  console.log('lag', lag, 'rebate entitled', entitled.toFixed(0), 'public_cost at t=60', r.final_frame.series.public_cost.toFixed(0));
  if (lag === 0 && Math.abs(r.final_frame.series.public_cost - entitled) > 1e-6) { console.log('BUG PRESENT'); process.exitCode = 1; }
}
