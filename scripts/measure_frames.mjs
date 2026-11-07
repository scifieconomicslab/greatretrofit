#!/usr/bin/env node
/* Frame-time matrix for a built Jette page: idle / playing / slider drag / wheel zoom, at far and near zoom.
 *   GPU=vulkan DPR=2 node scripts/measure_frames.mjs build/jette_retrofit.html out.json
 * Env: GPU=none|vulkan|egl (scripts/chrome_flags.mjs), DPR (default 1), CHROME. Frame time = gaps between requestAnimationFrame callbacks.
 * Prints and writes a JSON summary including what the GPU process reported (so a run can show it was or was not GPU-backed).
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { chromeFlags, gpuInfo } from './chrome_flags.mjs';

const page = path.resolve(process.argv[2] || 'build/jette_retrofit.html');
const outFile = process.argv[3];
const dpr = Number(process.env.DPR || 1);
const chrome = process.env.CHROME || (() => {
  const base = path.join(os.homedir(), '.cache/ms-playwright');
  const d = fs.readdirSync(base).filter(x => x.startsWith('chromium-') && !x.includes('headless')).sort().pop();
  return path.join(base, d, 'chrome-linux64/chrome');
})();
const port = 9300 + Math.floor(Math.random() * 500);
const proc = spawn(chrome, [...chromeFlags(), `--remote-debugging-port=${port}`, `--user-data-dir=${fs.mkdtempSync(path.join(os.tmpdir(), 'grchrome-'))}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let targets;
for (let i = 0; i < 50; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.length) break; } catch (e) {} await sleep(200); }
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pend = new Map();
ws.addEventListener('message', m => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { const p = pend.get(d.id); pend.delete(d.id); d.error ? p.rej(new Error(JSON.stringify(d.error))) : p.res(d.result); } });
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
const mouse = (type, x, y, extra = {}) => send('Input.dispatchMouseEvent', Object.assign({ type, x, y, button: 'left', buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1 }, extra));
const wheel = (x, y, dy) => send('Input.dispatchMouseEvent', { type: 'mouseWheel', x, y, deltaX: 0, deltaY: dy });

await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: dpr, mobile: false });
const t0 = Date.now();
await send('Page.navigate', { url: 'file://' + page });
for (let i = 0; i < 150; i++) { if (await ev('!!(window.labPack && labPack.binding && labPack.binding.bound && labPack.store.frame())').catch(() => false)) break; await sleep(300); }
const loadMs = Date.now() - t0; await sleep(1500);
await ev(`window.__ft = ms => new Promise(res => { const d = []; let last = performance.now(), t0 = last; const f = n => { d.push(n - last); last = n; if (n - t0 < ms) requestAnimationFrame(f); else { d.sort((a, b) => a - b); const s = d.reduce((a, b) => a + b, 0); res({ frames: d.length, fps: +(1000 * d.length / s).toFixed(1), mean_ms: +(s / d.length).toFixed(1), p50_ms: +d[d.length >> 1].toFixed(1), p95_ms: +d[Math.floor(d.length * .95)].toFixed(1), max_ms: +d[d.length - 1].toFixed(1) }); } }; requestAnimationFrame(f); });
  window.__btn = re => [...document.querySelectorAll('button')].find(b => re.test(b.textContent));`);
const canvas = await ev(`(() => { const c = [...document.querySelectorAll('canvas')].sort((a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight)[0]; const r = c.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height, pxw: c.width, pxh: c.height }; })()`);
const cx = canvas.x + canvas.w / 2, cy = canvas.y + canvas.h / 2;
const slider = await ev(`(() => { const s = [...document.querySelectorAll('input[type=range]')][0]; const r = s.getBoundingClientRect(); return { x: r.left, y: r.top + r.height / 2, w: r.width }; })()`);
const drag = async () => {
  await mouse('mouseMoved', slider.x + slider.w * 0.3, slider.y, { button: 'none', buttons: 0 });
  await mouse('mousePressed', slider.x + slider.w * 0.3, slider.y);
  const p = ev('__ft(3000)');
  for (let i = 0; i <= 30; i++) { await mouse('mouseMoved', slider.x + slider.w * (0.3 + 0.5 * i / 30), slider.y); await sleep(90); }
  const r = await p; await mouse('mouseReleased', slider.x + slider.w * 0.8, slider.y); return r;
};
const wheelPhase = async () => {   // zoom in 3 notches then out 3 notches, repeatedly, 3 s
  const p = ev('__ft(3000)');
  for (let k = 0; k < 10; k++) { for (let i = 0; i < 3; i++) { await wheel(cx, cy, -240); await sleep(40); } for (let i = 0; i < 3; i++) { await wheel(cx, cy, 240); await sleep(40); } await sleep(60); }
  return await p;
};
const phases = async () => {
  const R = {};
  if (process.env.IDLE_ONLY) { R.idle = await ev('__ft(4000)'); R.main_thread = await ev('window.__loaf'); return R; }
  R.idle = await ev('__ft(2000)');
  await ev('labPack.store.setTime(0)'); await sleep(500);
  await ev(`__btn(/Play/).click()`); R.playing = await ev('__ft(4000)'); R.months_played = await ev('labPack.store.time().t'); await ev(`__btn(/Pause/).click()`);
  R.slider_drag = await drag(); await sleep(2500); await ev('labPack.store.resetParams()'); await sleep(2000);
  R.wheel_zoom = await wheelPhase(); await sleep(1500);
  return R;
};
const out = { page: path.relative(process.cwd(), page), dpr, gpu_mode: process.env.GPU || 'none', gpu: await gpuInfo(port), canvas_css: [Math.round(canvas.w), Math.round(canvas.h)], canvas_px: [canvas.pxw, canvas.pxh],
  buildings: await ev('labPack.sim.buildings.length'), load_ms: loadMs };
out.loadavg_before = os.loadavg().map(x => +x.toFixed(1)); out.cpus = os.cpus().length;
if (process.env.IDLE_ONLY) await ev(`window.__loaf = { frames: 0, duration_ms: 0, script_ms: 0, render_ms: 0, blocking_ms: 0 }; new PerformanceObserver(l => { for (const e of l.getEntries()) { const L = window.__loaf; L.frames++; L.duration_ms += e.duration; L.script_ms += e.scripts.reduce((a, x) => a + x.duration, 0); L.render_ms += e.startTime + e.duration - e.renderStart; L.blocking_ms += e.blockingDuration; } }).observe({ type: 'long-animation-frame', buffered: false });`);
out.far = await phases();
if (process.env.IDLE_ONLY) { out.main_thread_note = 'long-animation-frame totals over the 4 s idle window: script_ms = JS, render_ms = style/layout/paint after JS'; console.log(JSON.stringify(out)); if (outFile) fs.writeFileSync(outFile, JSON.stringify(out, null, 1)); ws.close(); proc.kill(); process.exit(0); }
for (let i = 0; i < 7; i++) { await wheel(cx, cy, -240); await sleep(80); }
await sleep(3000);
out.near = await phases();
out.loadavg_after = os.loadavg().map(x => +x.toFixed(1));
console.log(JSON.stringify(out));
if (outFile) fs.writeFileSync(outFile, JSON.stringify(out, null, 1));
ws.close(); proc.kill();
