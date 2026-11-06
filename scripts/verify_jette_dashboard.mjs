#!/usr/bin/env node
/* (dashboard check: charts, KPIs, compare, P6 channels, tenure preset.) Drives the built Jette page in headless Chromium over the DevTools protocol (no playwright needed; Node 22+ has WebSocket).
 *   node scripts/verify_jette_browser.mjs [build/jette_retrofit.html] [docs/verification/dashboard]
 * Env: CHROME=/path/to/chrome (default: the playwright cache), DPR (default 1).
 * Writes screenshots to the output folder and prints a JSON summary (network requests, console, frame times, interaction checks).
 * Frame time = gap between requestAnimationFrame callbacks; software rendering in headless mode, so read it as a floor, not a GPU figure.
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const page = path.resolve(process.argv[2] || 'build/jette_retrofit.html');
const outDir = path.resolve(process.argv[3] || 'docs/verification/dashboard');
fs.mkdirSync(outDir, { recursive: true });
const dpr = Number(process.env.DPR || 1);
const chrome = process.env.CHROME || (() => {
  const base = path.join(os.homedir(), '.cache/ms-playwright');
  const d = fs.readdirSync(base).filter(x => x.startsWith('chromium-')).sort().pop();
  return path.join(base, d, 'chrome-linux64/chrome');
})();
const port = 9300 + Math.floor(Math.random() * 500);
const proc = spawn(chrome, ['--headless=new', '--no-sandbox', '--disable-gpu', `--remote-debugging-port=${port}`, `--user-data-dir=${fs.mkdtempSync(path.join(os.tmpdir(), 'grchrome-'))}`, 'about:blank'], { stdio: 'ignore' });
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

const R = { page: path.relative(process.cwd(), page), dpr, load_ms: loadMs };
await viewport(1440, 1500);
const text = () => ev(`document.body.innerText`);
R.binding = await ev(`({ bound: labPack.binding.bound, placed: labPack.binding.placed, warnings: labPack.binding.warnings })`);
await ev('labPack.store.setTime(0)'); await sleep(2500);
R.t0_text_has_NaN = /NaN/.test(await text());
R.t0_series = await ev(`JSON.stringify(labPack.store.frame().series.cost_parts)`);
await shot('d01_t0.jpg');
await ev('labPack.store.setTime(60)'); await sleep(2500);
const t60 = await text();
R.t60_has_NaN = /NaN/.test(t60);
R.dash = await ev(`({ svgs: document.querySelectorAll('svg').length, titles: [...document.querySelectorAll('svg title, svg desc')].map(x => x.textContent.slice(0, 160)), tiles: [...document.querySelectorAll('[class*=kpi]')].map(x => x.innerText.replace(/\\n/g, ' | ')).slice(0, 12) })`);
await shot('d02_t60_far.jpg');
await ev('labPack.store.setTime(120)'); await sleep(2500);
await shot('d03_t120_far.jpg');
R.t120_frame = await ev(`JSON.stringify(labPack.store.frame().series.buildings_by_state) + ' ' + JSON.stringify(labPack.store.frame().series.buildings_by_tenure)`);
// near zoom
const mc = await ev(`(() => { const c = [...document.querySelectorAll('canvas')].pop(); const r = c.getBoundingClientRect(); return { x: r.left + r.width * 0.5, y: r.top + r.height * 0.62 }; })()`);
for (let i = 0; i < 7; i++) { await wheel(mc.x, mc.y, -240); await sleep(80); }
await sleep(3500);
await shot('d04_t120_near.jpg');
await ev('labPack.store.setTime(180)'); await sleep(2500);
await shot('d05_t180_near.jpg');

// ---- a policy mix with more adoption, close up: segments, insulation, outline, tint ----
await ev(`labPack.store.applyPreset('public-service')`); await sleep(4000);
await ev('labPack.store.setTime(120)'); await sleep(2500);
for (let i = 0; i < 4; i++) { await wheel(mc.x, mc.y, -240); await sleep(80); }
await sleep(3500);
await shot('d06_public_t120_closer.jpg');
await ev(`labPack.store.applyPreset('rebate-only')`); await sleep(4000);
await ev('labPack.store.setTime(120)'); await sleep(2500);
await shot('d07_rebate_only_t120_closer.jpg');
// ---- A/B compare: A = rebate only, B = pass-through, then B = public service ----
const setCompare = async (on, bText) => ev(`(() => { const cb = document.querySelector('input[id^=pk-cmp]'); if (cb.checked !== ${on}) cb.click(); const sel = cb.closest('div,fieldset,section').querySelector('select'); if (sel && ${JSON.stringify(bText)}) { const o = [...sel.options].find(o => o.text === ${JSON.stringify(bText)}); sel.value = o.value; sel.dispatchEvent(new Event('change', { bubbles: true })); } return !!sel; })()`);
R.compare_pt = await setCompare(true, 'Pay the vendor direct'); await sleep(5000);
await ev('labPack.store.setTime(120)'); await sleep(2500);
for (let i = 0; i < 4; i++) { await wheel(mc.x, mc.y, 240); await sleep(80); }
await sleep(2500);
await shot('d08_compare_rebate_vs_passthrough.jpg');
R.compare_tiles_pt = await ev(`[...document.querySelectorAll('[class*=kpi]')].map(x => x.innerText.replace(/\\n/g, ' | ')).slice(0, 3)`);
R.compare_text_pt = await ev(`(document.body.innerText.match(/Map shows[^\\n]*/) || [''])[0]`);
await setCompare(true, 'Public retrofit service'); await sleep(5000);
await ev('labPack.store.setTime(120)'); await sleep(2500);
await shot('d09_compare_rebate_vs_public.jpg');
R.compare_tiles_pub = await ev(`[...document.querySelectorAll('[class*=kpi]')].map(x => x.innerText.replace(/\\n/g, ' | ')).slice(0, 3)`);
R.compare_has_NaN = /NaN/.test(await text());
await ev(`[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'B').click()`); await sleep(2500);
await shot('d10_compare_map_shows_B.jpg');
await setCompare(false, null); await sleep(1500);
// ---- tenure alternative ----
await ev(`labPack.store.applyPreset('more-rental')`); await sleep(4000);
await ev('labPack.store.setTime(120)'); await sleep(2500);
await ev(`[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Fit').click()`); await sleep(2500);
R.more_rental = await ev(`JSON.stringify(labPack.store.frame().series.buildings_by_tenure) + ' share ' + labPack.store.frame().series.rental_share`);
await shot('d11_more_rental_preset.jpg');
await ev(`labPack.store.resetParams()`); await sleep(3000);
R.legend = await ev(`[...document.querySelectorAll('[class*=legend]')].map(x => x.innerText.replace(/\\n/g, ' | ')).join(' ## ').slice(0, 2500)`);
R.controls = await ev(`[...document.querySelectorAll('button,input[type=checkbox],select')].map(b => (b.tagName + ':' + (b.textContent || b.getAttribute('aria-label') || b.id || '')).slice(0, 50))`);
const net = events.filter(e => e.method === 'Network.requestWillBeSent').map(e => e.params.request.url);
R.network_non_file = net.filter(u => !u.startsWith('file:') && !u.startsWith('blob:') && !u.startsWith('data:'));
R.console = events.filter(e => e.method === 'Runtime.exceptionThrown' || e.method === 'Log.entryAdded').map(e => e.method === 'Runtime.exceptionThrown' ? 'EXC ' + (e.params.exceptionDetails.exception?.description || e.params.exceptionDetails.text) : e.params.entry.level + ' ' + e.params.entry.text);
console.log(JSON.stringify(R, null, 2));
ws.close(); proc.kill();
