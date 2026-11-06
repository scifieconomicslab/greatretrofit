/* bind.js: scene buildings -> model buildings. node packs/great-retrofit/tests/test_bind.js */
'use strict';
const assert = require('assert');
const GR = require('../runtime.js');
const { bindScene, polygonArea } = require('../bind.js');
let failed = 0;
const test = (name, fn) => { try { fn(); console.log('PASS ' + name); } catch (e) { failed++; console.log('FAIL ' + name + '\n  ' + (e.stack || e)); } };
const rect = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];

test('polygon area is orientation independent', () => {
  assert.strictEqual(polygonArea(rect(0, 0, 10, 8)), 80);
  assert.strictEqual(polygonArea(rect(0, 0, 10, 8).reverse()), 80);
  assert.strictEqual(polygonArea([[0, 0], [1, 1]]), 0);
});

const old = { buildings: [   // older scene format: id, footprint, levels, osm
  { id: 'w1', footprint: rect(0, 0, 10, 10), levels: 2, osm: { building: 'terrace' } },
  { id: 'w2', footprint: rect(20, 0, 30, 20), levels: 5, osm: { building: 'apartments' } },
  { id: 'w3', footprint: rect(60, 0, 40, 40), levels: 1, osm: { building: 'industrial' } },
  { id: 'w4', footprint: [[0, 0], [1, 0]], levels: 2 },
  { id: 'w5', footprint: rect(0, 50, 12, 10) },
] };

test('older format: area from footprint, residential assumed, report counts the assumptions', () => {
  const r = bindScene(old, { sceneSeed: 5 });
  assert.strictEqual(r.report.scene_buildings, 5);
  assert.deepStrictEqual(r.excluded.map(x => x.join(':')), ['w3:non_residential', 'w4:invalid_geometry']);
  assert.deepStrictEqual(r.sceneIds, ['w1', 'w2', 'w5']);
  assert.strictEqual(r.report.assumed.area_from_footprint, 5);
  assert.strictEqual(r.report.assumed.residential, 5);
  assert.strictEqual(r.report.assumed.storeys_default, 1);
  assert.strictEqual(r.index.get('w2'), 1);
  assert.strictEqual(r.entities.building.count, 3);
  const w1 = r.entities.building.specs[0];   // 100 m2 x 2 storeys x 0.8 = 160 m2 gross -> 2 units
  assert.ok(Math.abs(w1.floor_area - 160) < 1e-9 && w1.units === 2);
});

test('same rows through the reference rules give the same buildings', () => {
  const r = bindScene(old, { sceneSeed: 5 });
  const rows = [{ id: 'w1', area: 100, storeys: 2, residential: true }, { id: 'w2', area: 600, storeys: 5, residential: true },
    { id: 'w3', area: 1600, storeys: 1, residential: false }, { id: 'w4', area: 0, storeys: 2, residential: true }, { id: 'w5', area: 120, storeys: 1, residential: true }];
  const e = GR.sceneEntities.buildEntities(rows, GR.sceneEntities.sceneRules(), 5);
  assert.deepStrictEqual(r.entities.building.specs, e.buildings);
});

test('newer format: area, height, residential and neighbours are used', () => {
  const s = { buildings: [
    { id: 'a', footprint: rect(0, 0, 10, 10), area: 250, height: 9.2, residential: true, neighbours: ['b'] },
    { id: 'b', footprint: rect(0, 0, 10, 10), area: 90, levels: 1, residential: false },
  ] };
  const r = bindScene(s);
  assert.strictEqual(r.report.assumed.area_from_footprint, 0);
  assert.strictEqual(r.report.assumed.residential, 0);
  assert.strictEqual(r.report.assumed.storeys_from_height, 1);   // 9.2 m -> 3 storeys
  assert.deepStrictEqual(r.neighbours.get('a'), ['b']);
  assert.deepStrictEqual(r.report.excluded, { non_residential: 1 });
  assert.ok(Math.abs(r.entities.building.specs[0].floor_area - 250 * 3 * 0.8) < 1e-9);
});

test('deterministic given the scene seed, and the seed matters', () => {
  const a = bindScene(old, { sceneSeed: 1 }), b = bindScene(old, { sceneSeed: 1 }), c = bindScene(old, { sceneSeed: 2 });
  assert.deepStrictEqual(a.entities, b.entities);
  assert.notDeepStrictEqual(a.entities.building.specs.map(x => x.unit_areas), c.entities.building.specs.map(x => x.unit_areas));
});

test('bound buildings drive the runtime', () => {
  const r = bindScene(old, { sceneSeed: 5 });
  const run = GR.runSimulation({ seed: 3, horizon_months: 24, buildings: r.entities.building.specs, credit_access: 'open' });
  assert.strictEqual(run.n_buildings, 3);
  assert.deepStrictEqual(run.final_frame.buildings.map(b => b.id), r.sceneIds);
});

test('empty and missing scenes bind to nothing', () => {
  assert.strictEqual(bindScene({}).entities.building.count, 0);
  assert.strictEqual(bindScene({ buildings: [] }).report.modelled, 0);
});
process.exit(failed ? 1 : 0);
