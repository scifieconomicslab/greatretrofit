/* Runs the shared vectors (validation_vectors.json) through the JS Params(). Prints [{name, accepted, error}].  node tests/model/validation_vectors.js */
'use strict';
const fs = require('fs'), path = require('path');
const GR = require(path.join(__dirname, '../../packs/great-retrofit/runtime.js'));
const dec = v => {
  if (Array.isArray(v)) return v.map(dec);
  if (v && typeof v === 'object') {
    if ('$' in v) return { NaN: NaN, Infinity: Infinity, '-Infinity': -Infinity }[v.$];
    return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, dec(x)]));
  }
  return v;
};
const doc = JSON.parse(fs.readFileSync(path.join(__dirname, 'validation_vectors.json'), 'utf8'));
const out = doc.vectors.map(v => {
  try {
    const p = GR.Params(dec(v.params));
    if (v.accept) { const sim = new GR.Simulation(Object.assign({}, p, { horizon_months: 2 })); sim.step(); sim.step(); }
    return { name: v.name, accepted: true };
  } catch (e) { return { name: v.name, accepted: false, error: String(e.message) }; }
});
console.log(JSON.stringify(out));
