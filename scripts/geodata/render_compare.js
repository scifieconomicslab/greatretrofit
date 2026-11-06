/* Renders Jette with and without real data, using the paperdolls renderer (read-only) and node-canvas.
 *   PD=/path/to/paperdolls node scripts/geodata/render_compare.js
 * Env: PD (paperdolls checkout, default ../scifirender/paperdolls), FLAT=cache/jette-commune-scene.json (the original scene),
 *   ENRICHED=build/jette-scene-enriched.json (terrain + UrbIS heights), OUT=docs/images/geodata, SHOTS=overview,hill,tall
 * Panels, same view each:  A flat, OSM storeys (assumed)  |  B flat, UrbIS storeys  |  C real relief x1 + UrbIS  |  D relief x3 + UrbIS.
 * Also prints, for the close shots, the building heights above the grid and the road-to-ground step statistics used in docs/calibration/geodata.md. */
const fs = require('fs'), path = require('path'), vm = require('vm');
const PD = process.env.PD || '/data/ScifiEconomicsLab/scifirender/paperdolls';
const { createCanvas } = require(path.join(PD, 'node_modules', 'canvas'));
const g = { console, Math, Object, Map, Array, Infinity, JSON, Set, Date, Int32Array, Uint8Array, Float32Array }; g.globalThis = g; vm.createContext(g);
for (const f of ['assetlib.js', 'buildinglib.js', 'treelib.js', 'vizlib.js', 'terrainlib.js']) vm.runInContext(fs.readFileSync(path.join(PD, 'viz', f), 'utf8'), g);
const A = g.AssetLib, V = g.VizLib; A.sprites.factory = (w, h) => createCanvas(w, h);
const pal = JSON.parse(fs.readFileSync(path.join(PD, 'assets', 'palettes.json'), 'utf8')), fam = pal.families.find(f => f.id === 'nw'), theme = A.theme(fam, undefined, 'colorfigures');
const load = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const FLAT = load(process.env.FLAT || 'cache/jette-commune-scene.json'), ENR = load(process.env.ENRICHED || 'build/jette-scene-enriched.json');
const OUT = process.env.OUT || 'docs/images/geodata', W = 1200, H = 700;
function stripZ(s) { const c = JSON.parse(JSON.stringify(s)); delete c.terrain; c.buildings.forEach(b => delete b.z); c.roads.forEach(r => delete r.z); c.trees.forEach(t => t.length = 2); return c; }
const variants = [
  { key: 'A', label: 'flat, OSM storeys (98.8% assumed)', scene: FLAT, relief: 1 },
  { key: 'B', label: 'flat, UrbIS 3D storeys', scene: stripZ(ENR), relief: 1 },
  { key: 'C', label: 'real relief x1 + UrbIS storeys', scene: ENR, relief: 1 },
  { key: 'D', label: 'real relief x3 + UrbIS storeys', scene: ENR, relief: 3 },
];
const B = V.sceneBounds(ENR);
const viewFor = (k, f, zmax) => { const cx = f ? f[0] : (B[0] + B[2]) / 2, cy = f ? f[1] : (B[1] + B[3]) / 2; return { w: W, h: H, scale: k, ox: W / 2 - (cx - cy) * k * 0.8660254, oy: H / 2 - (cx + cy) * k * 0.5 + (f ? (f[2] || 0) * k : zmax * k / 2) }; };
const T = ENR.terrain, at = (x, y) => { const u = (x - T.x0) / T.dx, v = (y - T.y0) / T.dy, i = Math.max(0, Math.min(T.nx - 2, Math.floor(u))), j = Math.max(0, Math.min(T.ny - 2, Math.floor(v))), fu = u - i, fv = v - j, z = T.z; const q = (a, b) => z[b * T.nx + a]; return (q(i, j) * (1 - fu) + q(i + 1, j) * fu) * (1 - fv) + (q(i, j + 1) * (1 - fu) + q(i + 1, j + 1) * fu) * fv; };   // z is a flat row-major array
const cen = b => b.centroid || [b.footprint.reduce((a, p) => a + p[0], 0) / b.footprint.length, b.footprint.reduce((a, p) => a + p[1], 0) / b.footprint.length];
function focusHill() {   // steepest ground among spots with at least 110 buildings within 120 m
  const cs = ENR.buildings.map(cen); let best = null;
  for (let i = 0; i < cs.length; i += 20) {
    const [x, y] = cs[i]; let n = 0; for (const q of cs) if (Math.abs(q[0] - x) < 120 && Math.abs(q[1] - y) < 120) n++;
    if (n < 110) continue; const sl = Math.hypot((at(x + 20, y) - at(x - 20, y)) / 40, (at(x, y + 20) - at(x, y - 20)) / 40);
    if (!best || sl > best.sl) best = { x, y, sl };
  } return [best.x, best.y];
}
function focusTall() { let b = null; for (const x of ENR.buildings) if (x.height_source === 'urbis3d' && (!b || x.height > b.height)) b = x; const c = cen(b); return [c[0] + 30, c[1] + 30]; }
const focus = { hill: process.env.FOCUS_HILL ? process.env.FOCUS_HILL.split(',').map(Number) : focusHill(), tall: process.env.FOCUS_TALL ? process.env.FOCUS_TALL.split(',').map(Number) : focusTall() };
console.log('focus hill', focus.hill.map(Math.round), 'tall', focus.tall.map(Math.round));
fs.mkdirSync(OUT, { recursive: true });
const sims = variants.map(v => V.createSim(JSON.parse(JSON.stringify(v.scene)), { seed: 5, theme, region: 'nw', relief: v.relief }));
sims.forEach(s => { for (let i = 0; i < 5; i++) V.stepSim(s, 0.1); });
for (const shot of (process.env.SHOTS || 'overview,hill,tall').split(',')) {
  const cols = 2, PW = 760, PH = 440, out = createCanvas(PW * cols, PH * 2), o = out.getContext('2d'); o.fillStyle = '#fff'; o.fillRect(0, 0, out.width, out.height);
  variants.forEach((v, i) => {
    const sim = sims[i]; A.sprites.cache.clear(); A.sprites.pixels = 0; sim._ground = sim._far = null; sim._zoom = sim._warm = null;
    const k = shot === 'overview' ? 0.2 : (shot === 'hill' ? 2.4 : 1.6), f = shot === 'overview' ? null : [focus[shot][0], focus[shot][1], v.scene.terrain ? at(focus[shot][0], focus[shot][1]) * v.relief : 0];
    const view = viewFor(k, f, sim.zmax); const cv = createCanvas(W, H), c = cv.getContext('2d'); sim.opts.sliceLayers = false; sim.opts.buildMs = 1e9;
    for (let n = 0; n < 8; n++) V.renderFrame(c, sim, view, {});
    const x = (i % cols) * PW, y = Math.floor(i / cols) * PH;
    if (shot === 'overview') { o.drawImage(cv, 0, 0, W, H, x, y, PW, PH); } else o.drawImage(cv, (W - PW) / 2, (H - PH) / 2, PW, PH, x, y, PW, PH);
    o.fillStyle = 'rgba(255,255,255,0.88)'; o.fillRect(x, y, 300, 22); o.fillStyle = '#222'; o.font = '13px sans-serif'; o.fillText(v.key + '  ' + v.label, x + 8, y + 15);
    o.strokeStyle = '#fff'; o.lineWidth = 2; o.strokeRect(x, y, PW, PH);
  });
  fs.writeFileSync(path.join(OUT, `jette-${shot}.jpg`), out.toBuffer('image/jpeg', { quality: 0.82 }));
  console.log('wrote', path.join(OUT, `jette-${shot}.jpg`));
}
