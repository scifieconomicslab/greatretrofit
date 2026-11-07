/* Shared loader for the fuzz harness and the repro scripts.
 * Loads, in one browser-like vm sandbox (no require, like the paperdolls page): paperdolls' viz/packruntime.js (read-only),
 * v3/js/prng.js, the pack's hook.js, runtime.js and bind.js, in the bundle's order. Nothing here modifies any of them.
 * Env: PAPERDOLLS_DIR (default /data/ScifiEconomicsLab/scifirender/paperdolls), PYTHON (default the repo venv, else python3).
 */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm'), cp = require('child_process');
const ROOT = path.resolve(__dirname, '..', '..', '..');
const PD_DIR = process.env.PAPERDOLLS_DIR || '/data/ScifiEconomicsLab/scifirender/paperdolls';
const VENV_PY = '/data/ScifiEconomicsLab/TheGreatRetrofit/.venv/bin/python';
const PY = process.env.PYTHON || (fs.existsSync(VENV_PY) ? VENV_PY : 'python3');

function available() { return fs.existsSync(path.join(PD_DIR, 'viz', 'packruntime.js')); }

function manifest() {
  const code = 'import sys,json,yaml;print(json.dumps(yaml.safe_load(open(sys.argv[1]))))';
  return JSON.parse(cp.execFileSync(PY, ['-c', code, path.join(ROOT, 'packs/great-retrofit/pack.yaml')], { encoding: 'utf8' }));
}

function load() {
  const g = { console, Math, Object, Map, Array, Infinity, NaN, JSON, Set, Date, Number, String, Int8Array, Int16Array, Int32Array, Float32Array, Float64Array, ArrayBuffer, Error, isFinite, structuredClone };
  g.globalThis = g; vm.createContext(g);
  const run = f => vm.runInContext(fs.readFileSync(f, 'utf8'), g, { filename: f });
  run(path.join(PD_DIR, 'viz', 'packruntime.js'));
  run(path.join(ROOT, 'v3/js/prng.js'));
  run(path.join(ROOT, 'packs/great-retrofit/hook.js'));
  run(path.join(ROOT, 'packs/great-retrofit/runtime.js'));
  run(path.join(ROOT, 'packs/great-retrofit/bind.js'));
  return { g, PR: g.PackRuntime, GR: g.GreatRetrofit, Bind: g.GreatRetrofitBind, impl: g.PaperDolls.getRuntime('great-retrofit') };
}

function defaults(m) { return Object.fromEntries(Object.entries(m.params).map(([k, v]) => [k, v.default])); }
module.exports = { ROOT, PD_DIR, PY, available, manifest, load, defaults };
