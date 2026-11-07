/* SM-9: toPackFrame stores units and units_done in Int16Array; a building of more than 32767 dwellings wraps to a negative count.
 * Reachable from a scene building with a huge footprint x levels (bad OSM geometry); bindScene accepts it (no upper bound on units).
 * Exit 1 while the bug is present. */
const E = require('../../../../tests/fuzz/lib/pack_env.js'); const { PR, impl, Bind } = E.load(), m = E.manifest(), defs = E.defaults(m);
const bound = PR.bindScene(m, impl, { buildings: [{ id: 'huge', area: 5000, levels: 800, residential: true }] });
const specs = bound.attrs.building.specs;
console.log('model units in the building:', specs[0].units);
const h = impl.init(defs, { building: { count: 1, attrs: bound.attrs.building } }, 1);
const f = impl.step(h, 0)[0].entities.building;
console.log('frame units field:', f.units[0], ' units_done:', f.units_done[0]);
if (f.units[0] !== specs[0].units) { console.log('BUG PRESENT: units wrapped'); process.exit(1); }
