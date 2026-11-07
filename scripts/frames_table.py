#!/usr/bin/env python3
"""Markdown tables from docs/verification/gpu/frames_*.json (written by scripts/measure_frames.mjs).
   python3 scripts/frames_table.py [dir]    cell = fps (p50 / p95 frame ms)"""
import glob, json, os, sys
d = sys.argv[1] if len(sys.argv) > 1 else 'docs/verification/gpu'
rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, 'frames_*.json')))]
order = {'none': 0, 'vulkan': 1, 'egl': 2, 'x11': 3}
rows.sort(key=lambda r: (r['page'], r['dpr'], order.get(r['gpu_mode'], 9)))
for zoom in ('far', 'near'):
    print(f'\n### {zoom} zoom\n\n| scene | DPR | mode | compositing / raster | idle | playing | slider drag | wheel zoom |\n|---|---|---|---|---|---|---|---|')
    for r in rows:
        c = lambda k: (lambda x: f"{x['fps']} ({x['p50_ms']} / {x['p95_ms']})")(r[zoom][k])
        print(f"| {'enriched' if 'enriched' in r['page'] else 'plain'} | {r['dpr']} | {r['gpu_mode']} | {r['gpu']['compositing'].replace('_software','-sw')} / {r['gpu']['rasterization'].replace('_software','-sw')} | {c('idle')} | {c('playing')} | {c('slider_drag')} | {c('wheel_zoom')} |")
