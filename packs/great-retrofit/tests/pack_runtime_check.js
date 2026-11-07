/* Runs the paperdolls pack checks on this pack's runtime, in a browser-like sandbox (no require, no module): the runtime must find
 * RetrofitPRNG as a global, register itself, produce frames that match the manifest, and be deterministic.
 *   node pack_runtime_check.js <paperdolls dir> <manifest.json>
 * Not a modification of paperdolls: it only reads viz/packvalidate.js and viz/packruntime.js.
 */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const [pdDir, manifestPath] = process.argv.slice(2);
if (!pdDir || !manifestPath) { console.error('usage: node pack_runtime_check.js <paperdolls dir> <manifest.json>'); process.exit(2); }
const pack = path.join(__dirname, '..');
const g = { console, Math, Object, Map, Array, Infinity, JSON, Set, Date, Number, String, Int8Array, Int16Array, Float32Array, Float64Array, ArrayBuffer, Error };
g.globalThis = g; vm.createContext(g);
const load = f => vm.runInContext(fs.readFileSync(f, 'utf8'), g, { filename: f });
load(path.join(pdDir, 'viz', 'packvalidate.js'));
load(path.join(pdDir, 'viz', 'packruntime.js'));
load(path.join(pack, 'prng.js'));
load(path.join(pack, 'runtime.js'));

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const PD = g.PaperDolls, impl = PD.getRuntime('great-retrofit');
let failed = 0;
const t = (name, bad) => { bad = Array.from(bad); console.log((bad.length ? 'FAIL ' : 'PASS ') + name + (bad.length ? ': ' + bad.join('; ') : '')); if (bad.length) failed++; };
t('runtime registered', impl ? [] : ['no runtime registered under great-retrofit']);
const v = g.PackSpec.validate(manifest);
t('manifest has no errors', v.errors);
t('deterministic and frames match the manifest (all presets)', [].concat(
  g.PackRuntime.checkRuntime(manifest, impl, {}, 24),
  ...manifest.presets.map(p => g.PackRuntime.checkRuntime(manifest, impl, p.params, 24).map(m => p.id + ': ' + m))));
process.exit(failed ? 1 : 0);
