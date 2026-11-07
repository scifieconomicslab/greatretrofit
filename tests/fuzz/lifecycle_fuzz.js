/* node tests/fuzz/lifecycle_fuzz.js <programs.json> <out.json>
 * Random handle-lifecycle programs against the pack runtime (as the paperdolls shell drives it through PackRuntime.create), checked against a reference
 * run of the same (params, seed) made on a fresh handle:
 *   start / step(n) / run(T) / setParams (policy rerun: restarts) / start again / two handles interleaved / chunking (step(1) x n == run(n)).
 * Also: a snapshot EMULATED by structuredClone of the Simulation's own fields (the runtime has no snapshot/restore) must continue exactly as the original.
 * Program: {id, params:[{p, seed, buildings}, ...], ops:[{op:'start',i}|{op:'step',n}|{op:'run',to}|{op:'setParams',i}|{op:'other',i,n}|{op:'clone',n}]}
 */
'use strict';
const fs = require('fs'), E = require('./lib/pack_env.js');
const { PR, GR, impl } = E.load(), manifest = E.manifest();
const H = manifest.time.steps;
const progs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const dig = f => PR.digest([f]);
const refCache = new Map();
function newRt(nb) { return PR.create(manifest, impl, { counts: { building: nb } }); }
function ref(spec, upTo) {
  const key = JSON.stringify([spec.p, spec.seed, spec.buildings]);
  if (!refCache.has(key)) {
    const rt = newRt(spec.buildings), fr = [rt.start(spec.p, spec.seed)].concat(rt.run(upTo));
    refCache.set(key, fr.map(dig));
  }
  return refCache.get(key);
}
function cloneSim(sim) {
  const own = {}; for (const k of Object.keys(sim)) if (k !== 'mode') own[k] = sim[k];
  const c = structuredClone(own);
  const s = Object.create(GR.Simulation.prototype); Object.assign(s, c); s.mode = GR.delivery[c.p.delivery_mode];
  return s;
}
const problems = [];
for (const prog of progs) {
  const bad = m => problems.push(`program ${prog.id}: ${m}`);
  try {
    const specs = prog.params, maxT = prog.max_t;
    const refs = specs.map(s => ref(s, maxT));
    let rt = null, cur = null, other = null, otherSpec = null;
    for (const [k, op] of prog.ops.entries()) {
      const where = `op#${k} ${JSON.stringify(op)}`;
      const check = (frames, from, spec, tag) => frames.forEach((f, j) => { const t = from + j; if (f.t !== t) bad(`${where}: frame t ${f.t}, want ${t}`); else if (dig(f) !== refs[spec][t]) bad(`${where}: ${tag} frame ${t} differs from a fresh run of the same parameters`); });
      if (op.op === 'start' || op.op === 'setParams') {
        const s = specs[op.i];
        if (op.op === 'start' || !rt) { rt = newRt(s.buildings); const f0 = rt.start(s.p, s.seed); check([f0], 0, op.i, 'start'); }
        else { const r = rt.setParams(Object.assign({}, s.p)); if (!r.restarted) bad(`${where}: rerun policy did not restart`); check([r.frame], 0, op.i, 'setParams'); }
        cur = op.i;
      } else if (rt === null) { continue; }
      else if (op.op === 'step') { const n = Math.min(op.n, maxT - rt.t); if (n > 0) { const t0 = rt.t; check(rt.step(n), t0 + 1, cur, 'step'); } }
      else if (op.op === 'run') { const t0 = rt.t, fr = rt.run(op.to); if (op.to <= t0 && fr.length) bad(`${where}: run to ${op.to} at t=${t0} returned frames`); check(fr, t0 + 1, cur, 'run'); if (rt.t !== Math.max(t0, Math.min(op.to, H))) bad(`${where}: rt.t ${rt.t}`); }
      else if (op.op === 'other') {   // a second, independent handle advanced in between
        if (!other) { otherSpec = op.i; other = newRt(specs[op.i].buildings); other.start(specs[op.i].p, specs[op.i].seed); }
        const n = Math.min(op.n, maxT - other.t); if (n > 0) { const t0 = other.t; check(other.step(n), t0 + 1, otherSpec, 'second handle'); }
      } else if (op.op === 'clone') {   // emulated snapshot/restore on a bare impl handle
        const s = specs[cur], h = impl.init(Object.assign({}, s.p), { building: { count: s.buildings } }, s.seed);
        impl.step(h, op.n);
        const snap = cloneSim(h.sim), a = impl.step(h, 6).map(dig), b = impl.step({ sim: snap }, 6).map(dig);
        if (JSON.stringify(a) !== JSON.stringify(b)) bad(`${where}: structuredClone snapshot does not continue as the original`);
        const again = impl.step({ sim: cloneSim(snap) }, 0)[0];
        if (again.t !== snap.t) bad(`${where}: clone of clone has t ${again.t}`);
      }
    }
  } catch (e) { bad(`threw ${e && e.message}`); }
}
fs.writeFileSync(process.argv[3], JSON.stringify(problems));
console.log(`ran ${progs.length} programs, ${problems.length} problem(s)`);
