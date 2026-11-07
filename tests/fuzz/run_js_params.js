/* node tests/fuzz/run_js_params.js <in.json> <out.json>: for each {name, value} (sentinels "$NaN", "$Inf", "$-Inf", "$undef") does the JS Params() accept it? */
'use strict';
const fs = require('fs'), E = require('./lib/pack_env.js');
const { GR } = E.load();
const dec = v => v === '$NaN' ? NaN : v === '$Inf' ? Infinity : v === '$-Inf' ? -Infinity : v === '$undef' ? undefined : v;
const items = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = items.map(({ name, value }) => {
  try { GR.Params({ [name]: dec(value) }); return { ok: true }; } catch (e) { return { ok: false, err: String(e.message) }; }
});
fs.writeFileSync(process.argv[3], JSON.stringify(out));
