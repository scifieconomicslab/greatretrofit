/* Informational (exit 0): what the lifecycle surface of the registered runtime is, and how PackRuntime treats it. SM-11 .. SM-14 in docs/state-machines.md. */
const E = require('../../../../tests/fuzz/lib/pack_env.js'); const { PR, impl } = E.load(), m = E.manifest(), defs = E.defaults(m);
console.log('runtime methods:', Object.keys(impl).join(', '), '| manifest on_params:', m.runtime.on_params);
const cont = JSON.parse(JSON.stringify(m)); cont.runtime.on_params = 'continue';
try { PR.create(cont, impl); } catch (e) { console.log('on_params: continue ->', e.message); }
const rt = PR.create(m, impl); rt.start(defs);
console.log('run(180) frames:', rt.run(180).length, '| run(180) again:', rt.run(180).length, '| t:', rt.t);
const s = rt.step(1); console.log('step(1) after the end -> frame t =', s[0].t, '(manifest time.steps =', m.time.steps + ')');
try { rt.step(0); } catch (e) { console.log('PackRuntime.step(0) ->', e.message); }
console.log('canSnapshot', rt.canSnapshot, '| canInspect', rt.canInspect);
const a = impl.init(defs, { building: { count: 5 } }, 1), b = impl.init(defs, { building: { count: 5 } }, 1);
impl.step(a, 30); console.log('second handle unaffected by the first: t =', impl.step(b, 0)[0].t);
