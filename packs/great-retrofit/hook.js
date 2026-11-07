/* hook.js: connects bind.js to the paperdolls runtime contract (docs/pack-spec.md, "Binding to the scene").
 * Loaded BEFORE runtime.js in the page (runtime.files order). It wraps PaperDolls.registerRuntime for the id 'great-retrofit' so that the registered runtime
 *  - gets a bindScene(scene) hook: { entities: {building: {count, attrs: {specs}}}, sceneIndex: {building: [scene id, ...]} }, made by bind.js
 *  - has init() read the bound specs from entities.building.attrs.specs (the shell hands attrs through) and pass them on as entities.building.specs.
 * runtime.js itself is not touched; it already takes entities.building.specs.
 */
(function (root) {
  'use strict';
  const PD = root.PaperDolls;
  if (!PD || typeof PD.registerRuntime !== 'function' || PD.__grHooked) return;
  PD.__grHooked = true;
  const orig = PD.registerRuntime.bind(PD);
  PD.registerRuntime = function (id, impl) {
    if (id !== 'great-retrofit') return orig(id, impl);
    const init = impl.init;
    const wrapped = Object.assign({}, impl, {
      init(p, ents, seed) {
        const b = ents && ents.building;
        if (b && b.attrs && b.attrs.specs && !b.specs) ents = Object.assign({}, ents, { building: Object.assign({}, b, { specs: b.attrs.specs }) });
        return init.call(this, p, ents, seed);
      },
      bindScene(scene) {
        const B = root.GreatRetrofitBind;
        if (!B) throw new Error('great-retrofit: bind.js is not loaded');
        const r = B.bindScene(scene, { sceneSeed: 1 });
        return { entities: { building: { count: r.entities.building.count, attrs: { specs: r.entities.building.specs } } }, sceneIndex: { building: r.sceneIds } };
      },
    });
    return orig(id, wrapped);
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
