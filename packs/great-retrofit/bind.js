/* bindScene(scene) -> entities for the Great Retrofit runtime (plan section 5.2, "model from scene").
 *
 * Turns scene buildings into model buildings and dwelling units with the scene-entities rules of the Python reference
 * (same code path as runtime.js sceneEntities.buildEntities; the rules and numbers are PLACEHOLDERS, see v3/docs/placeholders.md).
 *
 * Scene building fields used:
 *   id           required.
 *   footprint    [[x, y], ...] in metres (outer ring). Gives the area when `area` is absent (older scene format).
 *   area         footprint area in m2, if the scene exporter provides it (newer format; otherwise computed from the footprint).
 *   levels       storeys (older format; may be assumed by the exporter).  `storeys` is accepted as a synonym.
 *   height       metres; used for storeys (height / 3 m, rounded) only when levels is missing.
 *   residential  true / false when the exporter classifies it. Absent (older format): assumed residential unless osm.building
 *                names a clearly non-residential use; every such assumption is counted in the report.
 *   neighbours   ids of adjacent buildings; carried into the result untouched (the model does not use them yet).
 *
 * Returns {
 *   entities: { building: { count, specs } }   what the runtime's init() takes (specs: {id, tenure, unit_areas, units, floor_area})
 *   sceneIds:  scene id of each model building, in model order
 *   index:     Map scene id -> model building index
 *   neighbours: Map scene id -> ids
 *   excluded:  [[scene id, reason]]
 *   report:    {scene_buildings, modelled, excluded: {reason: n}, assumed: {area_from_footprint, residential, storeys_default, storeys_from_height}}
 * }
 * Where a building stands is the scene's; which tenure and how many units it gets is the model's, from the scene seed (not the model seed).
 */
(function (root) {
  'use strict';
  const GR = root.GreatRetrofit || (typeof require === 'function' ? require('./runtime.js') : null);
  if (!GR) throw new Error('bind.js needs runtime.js loaded first');
  const { buildEntities, sceneRules } = GR.sceneEntities;

  const NON_RESIDENTIAL = new Set(['commercial', 'industrial', 'retail', 'office', 'warehouse', 'church', 'chapel', 'cathedral', 'mosque', 'synagogue', 'temple',
    'school', 'kindergarten', 'university', 'college', 'hospital', 'civic', 'public', 'government', 'train_station', 'transportation', 'garage', 'garages',
    'carport', 'parking', 'shed', 'hangar', 'greenhouse', 'barn', 'farm_auxiliary', 'service', 'kiosk', 'roof', 'ruins', 'construction', 'sports_hall', 'stadium']);

  // Shoelace area of a polygon given as [[x, y], ...] (metres). Orientation-independent.
  function polygonArea(pts) {
    if (!Array.isArray(pts) || pts.length < 3) return 0;
    let s = 0;
    for (let i = 0, n = pts.length; i < n; i++) {
      const a = pts[i], b = pts[(i + 1) % n];
      s += a[0] * b[1] - b[0] * a[1];
    }
    return Math.abs(s) / 2;
  }

  function bindScene(scene, options) {
    options = options || {};
    const rules = sceneRules(options.rules), sceneSeed = options.sceneSeed || 0;
    const src = (scene && scene.buildings) || [];
    const assumed = { area_from_footprint: 0, residential: 0, storeys_default: 0, storeys_from_height: 0 };
    const rows = [], neighbours = new Map();
    for (const b of src) {
      let area = Number(b.area);
      if (!(area > 0)) { area = polygonArea(b.footprint); if (b.area === undefined || b.area === null) assumed.area_from_footprint++; }
      let storeys = Number(b.levels !== undefined && b.levels !== null ? b.levels : b.storeys);
      if (!(storeys > 0)) {
        if (Number(b.height) > 0) { storeys = Math.max(1, GR.pyRound(Number(b.height) / 3)); assumed.storeys_from_height++; }
        else { storeys = 1; assumed.storeys_default++; }
      }
      let residential;
      if (typeof b.residential === 'boolean') residential = b.residential;
      // paperdolls ingest writes 'residential' | 'probable' | 'other'. 'probable' (plain building=yes, 30 m2 or more) is a GUESS: included, and counted.
      else if (b.residential === 'residential' || b.residential === 'other') residential = b.residential === 'residential';
      else if (b.residential === 'probable') { residential = true; assumed.residential++; }
      else { residential = !NON_RESIDENTIAL.has(String((b.osm && b.osm.building) || '').toLowerCase()); assumed.residential++; }
      rows.push({ id: b.id, area, storeys, residential });
      if (Array.isArray(b.neighbours)) neighbours.set(String(b.id), b.neighbours.map(String));
    }
    const e = buildEntities(rows, rules, sceneSeed);
    const excludedBy = {};
    for (const [, why] of e.excluded) excludedBy[why] = (excludedBy[why] || 0) + 1;
    const index = new Map(e.scene_ids.map((id, i) => [id, i]));
    return {
      entities: { building: { count: e.buildings.length, specs: e.buildings } },
      sceneIds: e.scene_ids, index, neighbours, excluded: e.excluded,
      report: { scene_buildings: src.length, modelled: e.buildings.length, excluded: excludedBy, assumed },
    };
  }

  const api = { bindScene, polygonArea };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.GreatRetrofitBind = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
