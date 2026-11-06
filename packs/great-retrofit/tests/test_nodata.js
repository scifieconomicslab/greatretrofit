/* No-data in the pack frames. The v3 frame says null (v3/docs/frame-schema.md, "No-data"); the pack frame says NaN (paperdolls pack-spec, "entities").
 * Checks, over a whole default run and a run with no credit and no adopters: NaN appears only in the series the frame schema marks nullable,
 * exactly where the v3 frame has null; entity arrays never hold NaN or Infinity; every other series value is a finite number.
 *   node packs/great-retrofit/tests/test_nodata.js
 */
'use strict';
const R = require('../runtime.js');
let failed = 0;
const ok = (c, m) => { if (c) console.log('ok   ' + m); else { failed++; console.error('FAIL ' + m); } };

// pack series name -> how it is made from a v3 series point (only these may be NaN)
const NULLABLE = {
  rebate_per_euro: s => s.rebate_per_euro, can_front_cost: s => s.can_front_cost, cost_per_retrofit: s => [s.cost_per_retrofit],
  net_cash_by_quintile: s => s.net_cash_by_quintile, cost_parts: s => (s.cost_per_retrofit_parts ? [s.cost_per_retrofit_parts.base, s.cost_per_retrofit_parts.markup] : [null, null]),
};

function check(label, params) {
  const sim = new R.Simulation(R.Params(params));
  let frames = [sim.frame], sawNaN = false;
  for (let i = 0; i < params.horizon_months; i++) frames.push(sim.step());
  let bad = null;
  for (const fr of frames) {
    const pf = R.toPackFrame(fr);
    for (const [fname, arr] of Object.entries(pf.entities.building)) {
      for (let i = 0; i < arr.length; i++) if (!Number.isFinite(arr[i])) { bad = `t=${fr.t} entities.building.${fname}[${i}] = ${arr[i]}`; break; }
      if (bad) break;
    }
    for (const [sname, vals] of Object.entries(pf.series)) {
      const src = NULLABLE[sname] ? NULLABLE[sname](fr.series) : null;
      vals.forEach((v, i) => {
        if (bad) return;
        if (src) {
          const isNull = src[i] === null;
          if (isNull !== Number.isNaN(v)) bad = `t=${fr.t} series.${sname}[${i}]: v3 ${src[i]} but pack ${v}`;
          if (Number.isNaN(v)) sawNaN = true;
        } else if (!Number.isFinite(v)) bad = `t=${fr.t} series.${sname}[${i}] = ${v} (not declared nullable)`;
      });
    }
    if (bad) break;
  }
  ok(!bad, `${label}: NaN only where the v3 frame has null, none in entity arrays` + (bad ? ' -- ' + bad : ''));
  return sawNaN;
}

const saw = check('default run', { seed: 1, n_buildings: 24, horizon_months: 36 });
ok(saw, 'month 0 does have no-data points (so the check above is not vacuous)');
check('no credit, no savings (few adopters)', { seed: 2, n_buildings: 24, horizon_months: 36, credit_access: 'none', savings_scale: 0.0 });
process.exit(failed ? 1 : 0);
