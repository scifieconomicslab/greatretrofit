/* Chromium flags for the browser scripts. GPU=none (default, software, what the earlier runs used) | vulkan | egl | x11.
 *   GPU=x11     headful Chromium on the X display ($DISPLAY, here :0): Chromium's own default GPU path on a desktop
 *   GPU=vulkan  headless, ANGLE on Vulkan, GPU rasterisation forced      (verified on this machine: RTX 4080 SUPER via the NVIDIA Vulkan driver)
 *   GPU=egl     headless, ANGLE on desktop-GL EGL                        (verified: RTX 4080 SUPER, OpenGL ES 3.2 NVIDIA 580)
 * CHROME_FLAGS="--a --b" appends any extra flags. gpuInfo(send) reads SystemInfo.getInfo on a browser-level target. */
export function chromeFlags(mode = process.env.GPU || 'none') {
  const base = mode === 'x11' ? ['--no-sandbox'] : ['--headless=new', '--no-sandbox'];   // x11 = headful, needs DISPLAY (a real window appears)
  const m = { none: ['--disable-gpu'],
    vulkan: ['--use-angle=vulkan', '--enable-features=Vulkan', '--ignore-gpu-blocklist', '--enable-gpu-rasterization'],
    x11: ['--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--window-size=1500,1000', '--no-first-run', '--disable-features=Translate'],
    egl: ['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist', '--enable-gpu-rasterization'] }[mode];
  if (!m) throw new Error('GPU must be none, vulkan, egl or x11');
  return [...base, ...m, ...(process.env.CHROME_FLAGS ? process.env.CHROME_FLAGS.split(/\s+/).filter(Boolean) : [])];
}
export async function gpuInfo(port) {
  const v = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const ws = new WebSocket(v.webSocketDebuggerUrl); await new Promise(r => ws.addEventListener('open', r));
  const res = await new Promise(r => { ws.addEventListener('message', m => { const d = JSON.parse(m.data); if (d.id === 1) r(d.result); }); ws.send(JSON.stringify({ id: 1, method: 'SystemInfo.getInfo' })); });
  ws.close();
  const g = res.gpu || {}, f = g.featureStatus || {};
  return { renderer: g.auxAttributes?.glRenderer, compositing: f.gpu_compositing, rasterization: f.rasterization, canvas_oop: f.canvas_oop_rasterization, webgl: f.webgl, devices: (g.devices || []).map(d => d.deviceString || d.vendorString) };
}
