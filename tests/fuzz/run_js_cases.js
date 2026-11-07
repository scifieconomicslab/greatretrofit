/* node tests/fuzz/run_js_cases.js <cases.json> <out.json>
 * Runs every fuzz case (see fuzz_lib.py) on the JavaScript port, twice:
 *   core     runtime.js runSimulation(): v3 frames, events, votes (compared with Python frame by frame by test_fuzz_parity.py)
 *   adapter  the registered pack runtime through PackRuntime.create (frames checked against the manifest by paperdolls' own checkFrame)
 * Non-finite numbers are written as the strings "NaN" / "Infinity" so they cannot be mistaken for null. A case that throws is recorded with its message.
 */
'use strict';
const fs = require('fs');
const E = require('./lib/pack_env.js');
const [casesPath, outPath] = process.argv.slice(2);
const { PR, GR, impl } = E.load(), manifest = E.manifest();
const cases = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
const out = [];
for (const c of cases) {
  const rec = { kind: c.kind, seed: c.seed };
  const p = c.params;
  try {
    const r = GR.runSimulation(GR.Params(p));
    rec.core = JSON.parse(PR.digest({ frames: r.frames, events: r.events, votes: r.votes }));
  } catch (e) { rec.core_error = String(e && e.message || e); }
  try {
    const q = Object.assign({}, p); delete q.seed; delete q.buildings;
    const counts = p.buildings ? { building: p.buildings.length } : { building: p.n_buildings };
    const rt = PR.create(manifest, {
      init: (pp, ents, seed) => impl.init(pp, p.buildings ? { building: { count: ents.building.count, specs: p.buildings } } : ents, seed),
      step: impl.step, run: impl.run }, { counts });
    const frames = [rt.start(q, p.seed)];
    for (let i = 0; i < p.horizon_months; i++) frames.push(rt.step(1)[0]);
    rec.adapter = JSON.parse(PR.digest(frames));
  } catch (e) { rec.adapter_error = String(e && e.message || e); }
  out.push(rec);
}
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(`ran ${out.length} cases`);
