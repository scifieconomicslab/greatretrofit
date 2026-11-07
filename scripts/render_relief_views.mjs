#!/usr/bin/env node
/* Renders near and mid views of a built Jette page (enriched scene) at hill, steep and valley locations, to judge the real relief by eye.
 *   node scripts/render_relief_views.mjs build/jette_enriched.html docs/images/relief locations.json
 * locations.json: {"name": [x_m, y_m]} in scene metres (see the table in docs/verification/merged-build-gaps.md for how they were picked).
 * Env: GPU=none|vulkan|egl (default none: screenshots do not depend on it), DPR (default 1), W,H viewport (default 1800x1200). Uses window.labViewer.camera (paperdolls packhost).
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { chromeFlags } from './chrome_flags.mjs';

const page = path.resolve(process.argv[2]);
const outDir = path.resolve(process.argv[3] || 'docs/images/relief');
const locs = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const dpr = Number(process.env.DPR || 1);
const chrome = process.env.CHROME || path.join(os.homedir(), '.cache/ms-playwright', fs.readdirSync(path.join(os.homedir(), '.cache/ms-playwright')).filter(x => x.startsWith('chromium-') && !x.includes('headless')).sort().pop(), 'chrome-linux64/chrome');
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
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: Number(process.env.W || 1800), height: Number(process.env.H || 1200), deviceScaleFactor: dpr, mobile: false });
await send('Page.navigate', { url: 'file://' + page });
for (let i = 0; i < 150; i++) { if (await ev('!!(window.labPack && labPack.binding && labPack.binding.bound && labPack.store.frame() && window.labViewer)').catch(() => false)) break; await sleep(300); }
await sleep(2000);
// the map fills the stage: hide the side panels so the canvas is as large as the window lets it be is not possible without changing the page; clip to the canvas instead
const box = await ev(`(() => { const r = document.getElementById('stage').getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; })()`);
const info = await ev('({ min: labViewer.camera.minScale, max: labViewer.camera.maxScale, fit: labViewer.camera.fit, scale: labViewer.camera.scale })');
console.log(JSON.stringify({ box, info }));
const zoom = { mid: 0.5, near: 0.72 };
for (const [name, [x, y]] of Object.entries(locs)) for (const [zn, zf] of Object.entries(zoom)) {
  await ev(`(() => { const c = labViewer.camera; c.setZoomFraction(${zf}); c.cx = ${x}; c.cy = ${y}; if (c.clampCentre) c.clampCentre(); c.panScreen(0, 0); const cv = document.getElementById('stage'); cv.dispatchEvent(new WheelEvent('wheel', { deltaY: 0, clientX: ${box.x + box.width / 2}, clientY: ${box.y + box.height / 2}, bubbles: true })); })()`);
  await sleep(4500);
  const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 80, clip: { ...box, scale: 1 } });
  fs.writeFileSync(path.join(outDir, `${name}_${zn}.jpg`), Buffer.from(r.data, 'base64'));
  console.log(name, zn, await ev('JSON.stringify({ cx: Math.round(labViewer.camera.cx), cy: Math.round(labViewer.camera.cy), scale: +labViewer.camera.scale.toFixed(2) })'));
}
ws.close(); proc.kill();
