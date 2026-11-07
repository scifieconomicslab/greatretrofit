/* SM-7: a scene with no residential building binds to 0 model buildings, but init() falls back to the 200 synthetic ones (paramsFromPack: `else if (b && b.count)` is false for 0).
 * Exit 1 while the bug is present. */
const E = require('../../../../tests/fuzz/lib/pack_env.js'); const { PR, impl } = E.load(), m = E.manifest(), defs = E.defaults(m);
const bound = PR.bindScene(m, impl, { buildings: [{ id: 'shop', area: 100, levels: 2, residential: false }] });
console.log('bindScene ->', JSON.stringify(bound.counts));
const rt = PR.create(m, impl, { counts: bound.counts, attrs: bound.attrs });
try { rt.start(defs); console.log('start ok'); process.exit(0); }
catch (e) { console.log('BUG PRESENT: start() throws:', e.message); }
const rt2 = PR.create(m, impl, { counts: bound.counts, attrs: bound.attrs, validate: false });
const f = rt2.start(defs);
console.log('with validation off: frame carries', f.entities.building.state.length, 'buildings for a declared count of', rt2.entities.building.count);
process.exit(1);
