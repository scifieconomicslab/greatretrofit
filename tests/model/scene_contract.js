/* Scene/runtime contract (issue #3: SM-7, SM-8, SM-9). Loads the pack the way the page does (tests/fuzz/lib/pack_env.js: paperdolls packruntime.js is read-only).
 * node tests/model/scene_contract.js   -> exit 0 and "ok" lines, or the first failing assertion. */
'use strict';
const assert = require('assert');
const E = require('../fuzz/lib/pack_env.js');
if (!E.available()) { console.log('skip: paperdolls not available'); process.exit(0); }
const { PR, impl, GR, Bind } = E.load(), m = E.manifest(), defs = E.defaults(m);
const sq = (x, y) => [[x, y], [x + 10, y], [x + 10, y + 10], [x, y + 10]];
const eq = (a, b) => assert.strictEqual(JSON.stringify(a), JSON.stringify(b));
const ok = name => console.log('ok  ', name);

{ // SM-7: no residential building -> 0 model buildings, a clear message, no fallback to the 200 synthetic buildings
  const bound = PR.bindScene(m, impl, { buildings: [{ id: 'shop', area: 100, levels: 2, residential: false }, { id: 'tiny', area: 0, levels: 1, residential: true }] });
  eq(bound.counts, { building: 0 });
  const rt = PR.create(m, impl, { counts: bound.counts, attrs: bound.attrs });
  assert.throws(() => rt.start(defs), /no residential building to model \(0 model buildings\)/);
  const rt2 = PR.create(m, impl, { counts: bound.counts, attrs: bound.attrs, validate: false });
  assert.throws(() => rt2.start(defs), /no residential building/);          // with validation off it must not return a 200-building frame either
  assert.throws(() => impl.init(defs, { building: { count: 0 } }, 1), /no residential building/);
  assert.throws(() => impl.init(defs, { building: { count: 0, attrs: { specs: [] } } }, 1), /no residential building/);
  ok('SM-7 zero residential buildings: clear message, no synthetic fallback');
  const rt3 = PR.create(m, impl, { counts: { building: 12 } });             // not bound to a scene: the synthetic scene of the declared count still works
  assert.strictEqual(rt3.start(defs).entities.building.state.length, 12);
  ok('unbound runs with a declared count still work');
}

{ // SM-8: one id rule: "#<index in scene.buildings>"; every modelled building stands on a scene building
  const scene = { buildings: [{ footprint: sq(0, 0), levels: 2, residential: true }, { id: 'shop', footprint: sq(10, 0), levels: 1, residential: false },
    { id: null, footprint: sq(20, 0), levels: 2, residential: true }, { id: 7, footprint: sq(30, 0), levels: 2, residential: true }, { id: 'w1', footprint: sq(40, 0), levels: 3, residential: true }] };
  const r = PR.bindScene(m, impl, scene);
  eq(r.counts, { building: 4 });
  eq(Array.from(r.pos.building), [0, 2, 3, 4]);
  eq(r.warnings, []);
  const b = Bind.bindScene(scene);
  eq(b.sceneIds, ['#0', '#2', 7, 'w1']);               // number ids stay numbers, as paperdolls looks them up
  eq(b.entities.building.specs.map(s => s.id), ['#0', '#2', '7', 'w1']);
  assert.strictEqual(GR.sceneEntities.sceneKey(undefined, 5), '#5');
  assert.strictEqual(GR.sceneEntities.sceneKey(null, 0), '#0');
  assert.strictEqual(GR.sceneEntities.sceneKey(0, 3), '0');                 // id 0 is an id
  assert.strictEqual(GR.sceneEntities.sceneKey('', 3), '');                 // so is the empty string (paperdolls: only undefined/null are missing)
  const h = impl.init(defs, { building: { count: 4, attrs: r.attrs.building } }, 1);
  eq(h.sim.buildings.map(s => s.id), ['#0', '#2', '7', 'w1']);
  ok('SM-8 id-less and numeric ids: all modelled buildings are placed');
}

{ // SM-9: units in Int32Array, cap with a report for an absurd dwelling count
  const frame = { t: 0, buildings: [{ id: 'x', state: 'partial', tenure: 'condo', units: 40000, adopted_share: 0.5, income_q_mean: 3, shared_state: 'pending', vote_yes_share: 0, units_cannot_front: 0 }],
    series: { adoption_by_quintile: [0, 0, 0, 0, 0], rebate_per_euro: [null, null, null, null, null], can_front_cost: [null, null, null, null, null], cost_per_retrofit: null, public_cost: 0, bills_saved: 0,
      state_counts: { not_retrofitted: 0, partial: 1, retrofitted: 0, not_modelled: 0 }, cost_per_retrofit_parts: null, canvass_hours_by_quintile: [0, 0, 0, 0, 0], leisure_hours_by_quintile: [0, 0, 0, 0, 0],
      net_cash_by_quintile: [null, null, null, null, null], shared_counts: { pending: 1, approved: 0 }, tenure_counts: { owner_occupied: 0, condo: 1, rental: 0 } } };
  const f = GR.toPackFrame(frame).entities.building;
  assert.ok(f.units.constructor.name === 'Int32Array' && f.units_done.constructor.name === 'Int32Array');
  assert.strictEqual(f.units[0], 40000); assert.strictEqual(f.units_done[0], 20000);
  const scene = { buildings: [{ id: 'huge', area: 5000, levels: 800, residential: true }, { id: 'ok', area: 200, levels: 3, residential: true }] };
  const b = Bind.bindScene(scene);
  assert.strictEqual(GR.sceneEntities.MAX_UNITS_PER_BUILDING, 1000);
  eq(b.capped, [['huge', 40000]]);
  assert.strictEqual(b.report.capped, 1);
  assert.strictEqual(b.entities.building.specs[0].units, 1000);
  assert.ok(Math.abs(b.entities.building.specs[0].floor_area - 5000 * 800 * 0.8) < 1e-3 * 5000 * 800);    // floor area is kept
  const bound = PR.bindScene(m, impl, scene);
  const rt = PR.create(m, impl, { counts: bound.counts, attrs: bound.attrs });
  const fr = rt.start(defs).entities.building;
  assert.strictEqual(fr.units[0], 1000);
  ok('SM-9 Int32Array units and the dwelling cap');
  // non-finite geometry is invalid geometry, not a crash
  const e = GR.sceneEntities.buildEntities([{ id: 'a', area: Infinity, storeys: 2, residential: true }, { id: 'b', area: NaN, storeys: 2, residential: true }, { id: 'c', area: 1e308, storeys: 1e10, residential: true }], GR.sceneEntities.sceneRules(), 0);
  eq(e.excluded.map(x => x.join(':')), ['a:invalid_geometry', 'b:invalid_geometry', 'c:invalid_geometry']);
  ok('non-finite geometry is excluded');
}
