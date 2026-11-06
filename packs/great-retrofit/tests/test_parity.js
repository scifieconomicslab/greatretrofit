/* JS side of the parity check: run the JS runtime on every case in cases.json and compare with the golden
 * trajectories written by the Python reference (tools/regen_golden.py). Exact for integers, strings, booleans and null;
 * tolerance 1e-9 (relative to max(1, |x|)) for floats.   node packs/great-retrofit/tests/test_parity.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const R = require('../runtime.js');
const TOL = 1e-9;

function diff(want, got, where) {
  if (want === null || got === null || typeof want !== 'number' || typeof got !== 'number') {
    if (want === null || got === null || typeof want !== 'object' || typeof got !== 'object') {
      return want === got ? null : `${where}: want ${JSON.stringify(want)}, got ${JSON.stringify(got)}`;
    }
    if (Array.isArray(want) !== Array.isArray(got)) return `${where}: array vs object`;
    if (Array.isArray(want)) {
      if (want.length !== got.length) return `${where}: length want ${want.length}, got ${got.length}`;
      for (let i = 0; i < want.length; i++) { const d = diff(want[i], got[i], `${where}[${i}]`); if (d) return d; }
      return null;
    }
    const wk = Object.keys(want).sort(), gk = Object.keys(got).sort();
    if (wk.join() !== gk.join()) return `${where}: keys want ${wk}, got ${gk}`;
    for (const k of wk) { const d = diff(want[k], got[k], `${where}.${k}`); if (d) return d; }
    return null;
  }
  if (Number.isInteger(want)) return want === got ? null : `${where}: want ${want}, got ${got}`;   // integers (and states, by index) are exact
  return Math.abs(want - got) <= TOL * Math.max(1, Math.abs(want), Math.abs(got)) ? null : `${where}: want ${want}, got ${got}`;
}

const dir = path.join(__dirname);
const cases = JSON.parse(fs.readFileSync(path.join(dir, 'cases.json'), 'utf8'));
let failed = 0, n = 0;
function check(name, want, got) {
  n++;
  const d = diff(want, got, name);
  if (d) { failed++; console.error('FAIL ' + d); } else console.log('ok   ' + name);
}

for (const c of cases.cases) {
  const want = JSON.parse(fs.readFileSync(path.join(dir, 'golden', c.name + '.json'), 'utf8'));
  const r = R.runSimulation(c.params);
  check(c.name, want, { frames: r.frames, events: r.events, votes: r.votes, n_units: r.n_units, n_buildings: r.n_buildings });
}
const scenes = JSON.parse(fs.readFileSync(path.join(dir, 'golden', 'scene_tables.json'), 'utf8'));
for (const c of cases.scene_table_cases) {
  const e = R.sceneEntities.buildEntities(c.rows, R.sceneEntities.sceneRules(), c.scene_seed);
  check(c.name, scenes[c.name], {
    buildings: e.buildings.map(b => ({ id: b.id, tenure: b.tenure, unit_areas: b.unit_areas })), excluded: e.excluded,
  });
}

// the pack adapter: frames keep their shape and indices
{
  const p = R.Params({ seed: 1, n_buildings: 10, horizon_months: 3 });
  const sim = new R.Simulation(p);
  const f = R.toPackFrame(sim.frame);
  const ok = f.t === 0 && f.entities.building.state.length === 10 && f.series.adoption_by_quintile.length === 5 && f.series.buildings_by_state.length === 4;
  n++; if (!ok) { failed++; console.error('FAIL pack frame shape'); } else console.log('ok   pack frame shape');
}

console.log(failed ? `${failed} of ${n} FAILED` : `all ${n} parity checks passed`);
process.exit(failed ? 1 : 0);
