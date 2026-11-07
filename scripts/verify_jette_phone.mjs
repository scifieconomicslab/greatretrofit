#!/usr/bin/env node
/* Phone / tablet layout check of a built Jette page: device emulation with touch (Chromium over DevTools, no playwright).
 *   node scripts/verify_jette_phone.mjs build/jette_enriched.html docs/verification/phone
 * Env: GPU=none|vulkan|egl (chrome_flags.mjs), DPR (default 2).
 * For 390x844 and 768x1024: screenshots of the first screen, the controls, the charts, compare, and the inspector after a tap on a building.
 * Reports horizontal overflow, interactive elements smaller than 40 px, map size, and whether the inspector is in the viewport after a tap.
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { chromeFlags } from './chrome_flags.mjs';

const page = path.resolve(process.argv[2] || 'build/jette_retrofit.html');
const outDir = path.resolve(process.argv[3] || 'docs/verification/phone');
fs.mkdirSync(outDir, { recursive: true });
const dpr = Number(process.env.DPR || 2);
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
const shot = async (name, full = false) => { const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 72, captureBeyondViewport: full }); fs.writeFileSync(path.join(outDir, name), Buffer.from(r.data, 'base64')); return name; };
const tap = async (x, y) => { await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] }); await sleep(60); await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); };
await send('Page.enable'); await send('Runtime.enable');

const R = { page: path.relative(process.cwd(), page), dpr, sizes: {} };
for (const [w, h] of [[390, 844], [768, 1024]]) {
  const tag = `${w}x${h}`, S = R.sizes[tag] = {};
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dpr, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await send('Page.navigate', { url: 'file://' + page });
  for (let i = 0; i < 150; i++) { if (await ev('!!(window.labPack && labPack.binding && labPack.binding.bound && labPack.store.frame())').catch(() => false)) break; await sleep(300); }
  await sleep(2500);
  await ev('window.scrollTo(0,0)');
  S.first_screen = await shot(`${tag}_1_first_screen.jpg`);
  S.page = await ev(`({ scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth, scrollH: document.documentElement.scrollHeight, innerH: innerHeight,
    overflow_x: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    wide_elements: [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1; }).slice(0, 8).map(e => e.tagName + '#' + e.id + '.' + String(e.className).slice(0, 30) + ' right=' + Math.round(e.getBoundingClientRect().right)) })`);
  S.map = await ev(`(() => { const c = document.getElementById('stage'); const r = c.getBoundingClientRect(); return { x: Math.round(r.left), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height), share_of_viewport_height: +(r.height / innerHeight).toFixed(2) }; })()`);
  // tap targets
  S.small_targets = await ev(`(() => { const sel = 'button, a[href], input, select, textarea, summary, [role=button], [role=tab], [tabindex]:not([tabindex="-1"])';
    const out = []; for (const e of document.querySelectorAll(sel)) { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden') continue;
      const lab = e.closest('label'); const lr = lab ? lab.getBoundingClientRect() : r; const W = Math.max(r.width, e.type === 'range' ? 0 : lr.width), H = Math.max(r.height, lr.height > r.height && e.type !== 'range' ? lr.height : 0);
      if (W < 40 || H < 40) out.push({ el: e.tagName.toLowerCase() + (e.type ? '[' + e.type + ']' : ''), text: (e.textContent || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 28), w: Math.round(r.width), h: Math.round(r.height) }); }
    const total = document.querySelectorAll(sel).length; const tally = {}; out.forEach(o => { const k = o.el + ' ' + o.w + 'x' + o.h + (o.el === 'input[range]' ? '' : ' "' + o.text + '"'); tally[k] = (tally[k] || 0) + 1; });
    return { interactive_total: total, smaller_than_40px: out.length, by_size: tally, examples: out.slice(0, 12) }; })()`);
  const scrollToSel = async (sel, name, off = 0) => { const ok = await ev(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return false; window.scrollTo(0, e.getBoundingClientRect().top + scrollY - ${off}); return true; })()`); await sleep(500); if (ok) await shot(name); return ok; };
  S.controls_found = await scrollToSel('#left', `${tag}_2_controls.jpg`);
  S.charts_found = await scrollToSel('#bottom [class*=chart], #bottom svg, #bottom canvas', `${tag}_3_charts.jpg`, 10);
  S.compare_found = await scrollToSel('[class*=compare]', `${tag}_4_compare.jpg`, 10);
  await ev('window.scrollTo(0,0)'); await sleep(300);
  // tap a building: search a grid of points on the map canvas for one that selects something
  const box = await ev(`(() => { const r = document.getElementById('stage').getBoundingClientRect(); const t = Math.max(0, r.top), b = Math.min(innerHeight, r.bottom); return { x: r.left, y: t, w: r.width, h: Math.max(1, b - t) }; })()`);   // the part of the map that is on screen
  S.tap = null;
  for (let k = 0; k < 60 && !S.tap; k++) {
    const x = box.x + box.w * (0.2 + 0.6 * ((k * 0.618) % 1)), y = box.y + box.h * (0.2 + 0.6 * ((k * 0.382 + 0.1) % 1));
    await tap(x, y); await sleep(300);
    const sel = await ev('JSON.stringify(labPack.store.selection())');
    if (sel && sel !== 'null' && sel !== 'undefined') S.tap = { x: Math.round(x), y: Math.round(y), selection: sel.slice(0, 120) };
  }
  if (S.tap) {
    await sleep(500);
    S.inspector = await ev(`(() => { const e = document.querySelector('.pk-inspector'); if (!e) return { found: false }; const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
      const vis = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0)) * Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0)); return { found: true, display: cs.display, docked: e.classList.contains('pk-docked'), rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], scrollY: Math.round(scrollY),
      visible_share_in_viewport: +(vis / Math.max(1, r.width * r.height)).toFixed(2), text: e.innerText.slice(0, 200) }; })()`);
    await shot(`${tag}_5_inspector_after_tap.jpg`);
    await ev('window.scrollTo(0,0)'); await sleep(300); await shot(`${tag}_5b_inspector_top_of_page.jpg`);
  }
}
console.log(JSON.stringify(R, null, 1));
fs.writeFileSync(path.join(outDir, 'phone_summary.json'), JSON.stringify(R, null, 1));
ws.close(); proc.kill();
