/* SM-8: bind.js addresses a scene building without an id as "undefined" (String(undefined)), paperdolls as "#<index>" (sceneKey): such buildings are modelled but never drawn.
 * Exit 1 while the bug is present. */
const E = require('../../../../tests/fuzz/lib/pack_env.js'); const { PR, impl } = E.load(), m = E.manifest();
const sq = (x, y) => [[x, y], [x + 10, y], [x + 10, y + 10], [x, y + 10]];
const scene = { buildings: [{ footprint: sq(0, 0), levels: 2, residential: true }, { footprint: sq(20, 0), levels: 2, residential: true }, { id: 'w1', footprint: sq(40, 0), levels: 3, residential: true }] };
const r = PR.bindScene(m, impl, scene);
console.log('entities', JSON.stringify(r.counts), 'scene index of each entity', Array.from(r.pos.building), 'warnings', JSON.stringify(r.warnings));
const unplaced = Array.from(r.pos.building).filter(x => x < 0).length;
if (unplaced) { console.log('BUG PRESENT:', unplaced, 'modelled building(s) stand on no scene building'); process.exit(1); }
