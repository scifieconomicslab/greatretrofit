#!/usr/bin/env python3
"""Numbers behind 'do the real heights look right': ground spread under each footprint (how much a rigid sprite floats or sinks) and road grades,
from the 1 m DTM tiles and the scene that `paperdolls ingest --elevation` produced.
    python3 scripts/geodata/check_relief.py --scene build/jette-scene-enriched.json --tiles data/raw/dtm_wcs"""
import argparse, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frame import Frame
from lambert72 import lonlat_to_lambert72
from make_elevation import mosaic

ap = argparse.ArgumentParser(); ap.add_argument("--scene", default="build/jette-scene-enriched.json"); ap.add_argument("--tiles", default="data/raw/dtm_wcs")
a = ap.parse_args()
sc = json.load(open(a.scene)); fr = Frame(sc["area"]); big, x0, y1, sx, sy = mosaic(a.tiles)

def dtm(x, y):
    la, lo = fr.latlon(x, y); X, Y = lonlat_to_lambert72(lo, la)
    c, r = int((X - x0) / sx), int((y1 - Y) / sy)
    return big[r, c] if 0 <= r < big.shape[0] and 0 <= c < big.shape[1] else np.nan

span, diffz, tall_slope = [], [], []
for b in sc["buildings"]:
    zs = np.array([dtm(*p) for p in b["footprint"]]); zs = zs[np.isfinite(zs)]
    if len(zs) < 3: continue
    span.append(zs.max() - zs.min())
    if "z" in b: diffz.append(b["z"] - zs.mean())
span = np.array(span)
res = {"buildings_measured": len(span), "footprint_ground_span_m": {"median": float(np.median(span)), "p90": float(np.percentile(span, 90)), "p99": float(np.percentile(span, 99)), "max": float(span.max()),
       "share_over_1m": float(np.mean(span > 1)), "share_over_2m": float(np.mean(span > 2))},
       "scene_z_minus_dtm_mean_under_footprint_m": {"median": float(np.median(diffz)), "p95_abs": float(np.percentile(np.abs(diffz), 95))}}
grades, steps, bridges = [], [], []
for r in sc["roads"]:
    if "z" not in r or len(r["pts"]) < 2: continue
    P, Z = r["pts"], r["z"]
    for i in range(len(P) - 1):
        L = math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1])
        if L > 1.0: grades.append(abs(Z[i + 1] - Z[i]) / L)
    if max(abs(Z[i + 1] - Z[i]) for i in range(len(Z) - 1)) > 3.0: bridges.append(r["id"])
g = np.array(grades)
res["road_grade"] = {"segments": int(len(g)), "median_pct": float(np.median(g) * 100), "p99_pct": float(np.percentile(g, 99) * 100), "max_pct": float(g.max() * 100), "share_over_10pct": float(np.mean(g > 0.10)),
                     "roads_with_a_3m_step_between_points": len(bridges), "ids": bridges[:10]}
print(json.dumps(res, indent=1))
