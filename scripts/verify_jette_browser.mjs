#!/usr/bin/env node
/* Drives the built Jette page in headless Chromium over the DevTools protocol (no playwright needed; Node 22+ has WebSocket).
 *   node scripts/verify_jette_browser.mjs [build/jette_retrofit.html] [docs/verification]
 * Env: CHROME=/path/to/chrome (default: the playwright cache), DPR (default 1), GPU=none|vulkan|egl (default none = software; see chrome_flags.mjs).
 * Writes screenshots to the output folder and prints a JSON summary (network requests, console, frame times, interaction checks).
 * Frame time = gap between requestAnimationFrame callbacks; with GPU=none this is software rendering, so read it as a floor; the summary's gpu field says what actually rendered.
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { chromeFlags, gpuInfo } from './chrome_flags.mjs';

const page = path.resolve(process.argv[2] || 'build/jette_retrofit.html');
const outDir = path.resolve(process.argv[3] || 'docs/verification');
fs.mkdirSync(outDir, { recursive: true });
const dpr = Number(process.env.DPR || 1);
const chrome = process.env.CHROME || (() => {
  const base = path.join(os.homedir(), '.cache/ms-playwright');
  const d = fs.readdirSync(base).filter(x => x.startsWith('chromium-')).sort().pop();
  return path.join(base, d, 'chrome-linux64/chrome');
})();
const port = 9300 + Math.floor(Math.random() * 500);
const proc = spawn(chrome, [...chromeFlags(), `--remote-debugging-port=${port}`, `--user-data-dir=${fs.mkdtempSync(path.join(os.tmpdir(), 'grchrome-'))}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let targets;
for (let i = 0; i < 50; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.length) break; } catch (e) {} await sleep(200); }
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pend = new Map(); const events = [];
ws.addEventListener('message', m => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { const p = pend.get(d.id); pend.delete(d.id); d.error ? p.rej(new Error(JSON.stringify(d.error))) : p.res(d.result); } else events.push(d); });
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
const viewport = (w, h) => send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dpr, mobile: false });
const shot = async (name, quality = 70) => { const r = await send('Page.captureScreenshot', { format: 'jpeg', quality }); fs.writeFileSync(path.join(outDir, name), Buffer.from(r.data, 'base64')); return name; };
const mouse = (type, x, y, extra = {}) => send('Input.dispatchMouseEvent', Object.assign({ type, x, y, button: 'left', buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1 }, extra));
const click = async (x, y) => { await mouse('mouseMoved', x, y, { button: 'none', buttons: 0 }); await mouse('mousePressed', x, y); await mouse('mouseReleased', x, y); };
const wheel = (x, y, dy) => send('Input.dispatchMouseEvent', { type: 'mouseWheel', x, y, deltaX: 0, deltaY: dy });

await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable'); await send('Log.enable');
await viewport(1440, 900);
const t0 = Date.now();
await send('Page.navigate', { url: 'file://' + page });
for (let i = 0; i < 100; i++) { if (await ev('!!(window.labPack && labPack.binding && labPack.binding.bound && labPack.store.frame())').catch(() => false)) break; await sleep(300); }
const loadMs = Date.now() - t0;
await sleep(1500);

// rAF frame-time probe, installed in the page
await ev(`window.__ft = ms => new Promise(res => { const d = []; let last = performance.now(), t0 = last; const f = n => { d.push(n - last); last = n; if (n - t0 < ms) requestAnimationFrame(f); else { d.sort((a, b) => a - b); const s = d.reduce((a, b) => a + b, 0); res({ frames: d.length, mean_ms: +(s / d.length).toFixed(1), p50_ms: +d[d.length >> 1].toFixed(1), p95_ms: +d[Math.floor(d.length * .95)].toFixed(1), max_ms: +d[d.length - 1].toFixed(1) }); } }; requestAnimationFrame(f); });
  window.__btn = re => [...document.querySelectorAll('button')].find(b => re.test(b.textContent));
  window.__month = () => labPack.store.time().t;`);

const R = { page: path.relative(process.cwd(), page), dpr, gpu_mode: process.env.GPU || 'none', gpu: await gpuInfo(port), load_ms: loadMs };
R.binding = await ev(`({ ok: labPack.binding.ok, bound: labPack.binding.bound, placed: labPack.binding.placed, count: labPack.binding.count, nScene: labPack.binding.nScene, warnings: labPack.binding.warnings,
  scene_buildings: labPack.sim.buildings.length, mode: labPack.controller.mode, error: labPack.controller.error, banner: document.body.innerText.split('\\n').filter(l => /placed/.test(l))[0] })`);
R.first_frame = await ev(`JSON.stringify(labPack.store.frame().series.buildings_by_state)`);
await shot('01_far_start.jpg');

// ---- frame time, far zoom ----
R.frame_far = {};
R.frame_far.idle = await ev('__ft(2000)');
await ev('labPack.store.setTime(0)'); await sleep(500);
await ev(`__btn(/Play/).click()`);
R.frame_far.playing = await ev('__ft(5000)');
R.frame_far.months_played = await ev('__month()');
await shot('02_far_playing.jpg');
await ev(`__btn(/Pause/).click()`);
// slider drag at far zoom: change the rebate rate through the DOM slider and time the frames
const slider = await ev(`(() => { const s = [...document.querySelectorAll('input[type=range]')][0]; const r = s.getBoundingClientRect(); return { x: r.left, y: r.top + r.height / 2, w: r.width, id: s.id || s.name || s.getAttribute('aria-label') }; })()`);
const drag = async () => {
  await mouse('mouseMoved', slider.x + slider.w * 0.3, slider.y, { button: 'none', buttons: 0 });
  await mouse('mousePressed', slider.x + slider.w * 0.3, slider.y);
  const p = ev('__ft(3000)');
  for (let i = 0; i <= 30; i++) { await mouse('mouseMoved', slider.x + slider.w * (0.3 + 0.5 * i / 30), slider.y); await sleep(90); }
  const r = await p; await mouse('mouseReleased', slider.x + slider.w * 0.8, slider.y); return r;
};
R.frame_far.slider_drag = await drag();
await sleep(2500);
R.frame_far.after_slider = await ev(`({ params: labPack.store.params(), runs: labPack.controller.runs, last_run_ms: Math.round(labPack.controller.lastRunMs) })`);
await shot('03_far_after_slider.jpg');
await ev(`labPack.store.resetParams()`); await sleep(2500);

// ---- zoom in (wheel) ----
for (let i = 0; i < 7; i++) { await wheel(700, 560, -240); await sleep(80); }
await sleep(3000);
await shot('04_near.jpg');
R.frame_near = {};
R.frame_near.idle = await ev('__ft(2000)');
await ev('labPack.store.setTime(0)'); await sleep(500);
await ev(`__btn(/Play/).click()`);
R.frame_near.playing = await ev('__ft(5000)');
R.frame_near.months_played = await ev('__month()');
await ev(`__btn(/Pause/).click()`);
R.frame_near.slider_drag = await drag();
await sleep(2500);
await shot('05_near_after_slider.jpg');
await ev(`labPack.store.resetParams()`); await sleep(2500);

// ---- picking and inspector ----
await ev('labPack.store.setTime(60)'); await sleep(1500);
R.pick = [];
const canvas = await ev(`(() => { const c = [...document.querySelectorAll('canvas')].pop(); const r = c.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; })()`);
for (let k = 0; k < 40 && R.pick.length < 3; k++) {
  const x = canvas.x + canvas.w * (0.25 + 0.5 * ((k * 0.618) % 1)), y = canvas.y + canvas.h * (0.25 + 0.5 * ((k * 0.382 + 0.1) % 1));
  await click(x, y); await sleep(250);
  const sel = await ev('JSON.stringify(labPack.store.selection())');
  if (sel && sel !== 'null' && sel !== 'undefined') R.pick.push({ x: Math.round(x), y: Math.round(y), selection: sel });
}
R.inspector_text = await ev(`(() => { const e = [...document.querySelectorAll('*')].filter(e => /inspector/i.test(e.className + e.id)); return e.map(x => x.innerText).join(' | ').slice(0, 800); })()`);
await shot('06_selected_inspector.jpg');
await mouse('mouseMoved', canvas.x + canvas.w * 0.4, canvas.y + canvas.h * 0.4, { button: 'none', buttons: 0 });
await sleep(300); await shot('07_hover_tooltip.jpg');
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
R.after_escape = await ev('JSON.stringify(labPack.store.selection())');

// ---- parameter changes: delivery mode, wall colouring, presets ----
await ev(`labPack.store.applyPreset('public-service')`); await sleep(3000);
R.preset_public = await ev(`JSON.stringify(labPack.store.frame().series.buildings_by_state) + ' @t=' + labPack.store.time().t`);
await shot('08_preset_public_service.jpg');
await ev(`labPack.store.resetParams()`); await sleep(2000);
R.wall_choices = await ev(`[...document.querySelectorAll('select')].map(s => ({ label: (s.previousElementSibling || s.parentElement).textContent.slice(0, 40), options: [...s.options].map(o => o.text) }))`);

// ---- narrow viewport ----
await viewport(390, 844);
await sleep(2000);
await shot('09_narrow_390.jpg');
R.narrow = await ev(`({ scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth, overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  canvas: [...document.querySelectorAll('canvas')].map(c => { const r = c.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }) })`);
await viewport(768, 1024); await sleep(1500); await shot('10_tablet_768.jpg');
await viewport(1440, 900); await sleep(1000);

// ---- network and console ----
const net = events.filter(e => e.method === 'Network.requestWillBeSent').map(e => e.params.request.url);
R.network_requests = net.map(u => u.length > 100 ? u.slice(0, 100) + '...' : u);
R.network_non_file = net.filter(u => !u.startsWith('file:') && !u.startsWith('blob:') && !u.startsWith('data:'));
R.console = events.filter(e => e.method === 'Runtime.consoleAPICalled' || e.method === 'Runtime.exceptionThrown' || e.method === 'Log.entryAdded')
  .map(e => e.method === 'Runtime.exceptionThrown' ? 'EXC ' + (e.params.exceptionDetails.exception?.description || e.params.exceptionDetails.text) : e.method === 'Log.entryAdded' ? e.params.entry.level + ' ' + e.params.entry.text : e.params.type + ' ' + e.params.args.map(a => a.value ?? a.description).join(' '));
console.log(JSON.stringify(R, null, 2));
ws.close(); proc.kill();
