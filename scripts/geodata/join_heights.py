#!/usr/bin/env python3
"""Join UrbIS 3D building heights to the OSM-derived scene buildings and write an enriched scene.

    python3 scripts/geodata/join_heights.py --scene cache/jette-commune-scene.json \\
        --gpkg data/raw/urbis3d/x/gpkg/UrbISBuildings3D_21010.gpkg --out build/jette-scene-enriched.json [--dtm-tiles data/raw/dtm_wcs]

Needs numpy and shapely (pip install shapely). The original scene is never modified.

Method
  1. UrbIS solids (EPSG:31370, LoD2) are reduced to footprint + ridge height + eave height (urbis3d.py), then moved into the scene frame
     (Lambert 72 -> lon/lat -> Frame.xy, the same formulas paperdolls' LocalFrame uses).
  2. Spatial index (shapely STRtree) over UrbIS footprints; for each scene building the intersection area with every candidate.
     cover(c) = area(osm ∩ c) / area(osm).
       good       best cover >= MIN_COVER (0.5) and no other candidate with cover >= COMPETE (0.25)
       multi      the scene building overlaps several UrbIS solids (best >= 0.5 with a competitor, or best >= 0.3 and the candidates jointly cover
                  >= 0.6) and their ridge heights agree within AGREE_M (1.5 m): the best candidate is used
       ambiguous  overlaps several UrbIS solids whose heights disagree: no height is applied
       weak       best cover between 0.3 and 0.5 with nothing to back it: no height applied
       unmatched  best cover < 0.3 or no overlap
  3. Applied for good and multi: height = UrbIS ridge height (m, ground to highest roof point), height_eave, ground_z (m, from UrbIS), height_source,
     height_match (class), urbis_id. levels = max(1, round(eave height / STOREY_M)) unless OSM had a building:levels tag (then OSM's value is kept and
     the disagreement is counted), levels_assumed = False, osm.levels_source = "urbis3d". Nothing is applied for ambiguous, weak, unmatched.
The storey count from height is an estimate (floor-to-floor 3.0 m, +-1 storey is normal); it is far better than the 2-storey default.
"""
import argparse, collections, json, math, os, statistics, sys

import numpy as np
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frame import Frame                         # noqa: E402
from lambert72 import lambert72_to_lonlat       # noqa: E402

MIN_COVER, WEAK_COVER, COMPETE, JOINT_COVER, AGREE_M, STOREY_M = 0.5, 0.3, 0.25, 0.6, 1.5, 3.0
ASSUMED = ("type-default", "global-default")


def classify_match(covers, heights, min_cover=MIN_COVER, weak=WEAK_COVER, compete=COMPETE, joint=JOINT_COVER, agree_m=AGREE_M):
    """covers/heights: parallel lists for the candidate solids, sorted by cover descending. -> (class, index of the solid to use or None)."""
    if not covers or covers[0] < weak:
        return "unmatched", None
    rivals = [i for i in range(1, len(covers)) if covers[i] >= compete]
    if covers[0] >= min_cover and not rivals:
        return "good", 0
    pool = [0] + rivals if covers[0] >= min_cover else [i for i in range(len(covers)) if covers[i] >= 0.1]
    agree = max(heights[i] for i in pool) - min(heights[i] for i in pool) <= agree_m
    if covers[0] >= min_cover:
        return ("multi", 0) if agree else ("ambiguous", None)
    if len(pool) > 1 and sum(covers[i] for i in pool) >= joint:
        return ("multi", 0) if agree else ("ambiguous", None)
    return "weak", None


def to_scene_polygon(rings, frame):
    """UrbIS XY rings in EPSG:31370 -> shapely polygon in the scene frame."""
    pts = []
    for x, y in rings:
        lon, lat = lambert72_to_lonlat(x, y)
        pts.append(frame.xy(lat, lon))
    p = Polygon(pts)
    return p if p.is_valid else p.buffer(0)


def join(scene, urbis, storey_m=STOREY_M, source="UrbIS 3D Buildings (Brussels, LoD2)"):
    """scene: dict (not modified). urbis: list of dicts from urbis3d.read_buildings with 'poly' (scene-frame shapely geometry) added.
    -> (enriched scene dict, report dict)."""
    import copy
    out = copy.deepcopy(scene)
    cand = [u for u in urbis if u.get("ridge_h") is not None and u["poly"].area > 0]
    tree = STRtree([u["poly"] for u in cand])
    classes = collections.Counter()
    used = collections.defaultdict(list)
    tag_pairs = []
    levels_before = collections.Counter(b["osm"]["levels_source"] for b in scene["buildings"])
    for b in out["buildings"]:
        poly = Polygon(b["footprint"])
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.area <= 0:
            classes["unmatched"] += 1
            b["height_match"] = "unmatched"
            continue
        idx = tree.query(poly, predicate="intersects")
        rows = []
        for i in idx:
            a = poly.intersection(cand[i]["poly"]).area
            if a > 0.5:
                rows.append((a / poly.area, i))
        rows.sort(reverse=True)
        covers = [r[0] for r in rows]
        hs = [cand[r[1]]["ridge_h"] for r in rows]
        cls, k = classify_match(covers, hs, ) if rows else ("unmatched", None)
        classes[cls] += 1
        b["height_match"] = cls
        if k is None:
            continue
        u = cand[rows[k][1]]
        used[u["id"]].append(b["id"])
        b["height"] = round(u["ridge_h"], 1)
        b["height_eave"] = round(u["eave_h"], 1)
        b["ground_z"] = round(u["ground_z"], 1)
        b["height_source"] = "urbis3d"
        b["urbis_id"] = u["id"]
        b["height_cover"] = round(covers[k], 2)
        derived = max(1, int(round(u["eave_h"] / storey_m)))
        if b["osm"].get("levels_source") == "tag":
            tag_pairs.append((b["levels"], derived))
        else:
            b["levels"] = derived
            b["osm"]["levels_source"] = "urbis3d"
        b["levels_assumed"] = False
    n = len(out["buildings"])
    after = collections.Counter(b["osm"]["levels_source"] for b in out["buildings"])
    assumed_before = sum(1 for b in scene["buildings"] if b["levels_assumed"])
    assumed_after = sum(1 for b in out["buildings"] if b["levels_assumed"])
    solids_multi = sum(1 for v in used.values() if len(v) > 1)
    urb_unused = [u for u in cand if u["id"] not in used]
    rep = {
        "scene_buildings": n, "urbis_solids": len(urbis), "urbis_with_roof": len(cand),
        "match_classes": dict(classes), "match_rate_applied": (classes["good"] + classes["multi"]) / n if n else 0.0,
        "levels_assumed_before": assumed_before, "levels_assumed_after": assumed_after,
        "levels_assumed_share_before": assumed_before / n if n else 0.0, "levels_assumed_share_after": assumed_after / n if n else 0.0,
        "levels_source_before": dict(levels_before), "levels_source_after": dict(after),
        "urbis_solids_matched_by_several_scene_buildings": solids_multi,
        "urbis_solids_not_used": len(urb_unused),
        "urbis_not_used_area_median_m2": statistics.median(u["poly"].area for u in urb_unused) if urb_unused else 0,
        "osm_tag_levels_vs_urbis": None,
    }
    if tag_pairs:
        d = [a - b for a, b in tag_pairs]
        rep["osm_tag_levels_vs_urbis"] = {"n": len(d), "same": sum(1 for x in d if x == 0), "within_1": sum(1 for x in d if abs(x) <= 1),
                                           "mean_diff_osm_minus_urbis": statistics.fmean(d)}
    hs = [b["height"] for b in out["buildings"] if b.get("height_source") == "urbis3d"]
    if hs:
        q = statistics.quantiles(hs, n=10)
        rep["applied_height_deciles_m"] = [round(x, 1) for x in q]
        lv = collections.Counter(b["levels"] for b in out["buildings"] if b.get("height_source") == "urbis3d")
        rep["applied_levels_hist"] = {str(k): lv[k] for k in sorted(lv)}
    out.setdefault("area", {})["heights"] = {"source": source, "storey_m": storey_m, "classes": dict(classes)}
    return out, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", default="cache/jette-commune-scene.json")
    ap.add_argument("--gpkg", default="data/raw/urbis3d/x/gpkg/UrbISBuildings3D_21010.gpkg")
    ap.add_argument("--out", default="build/jette-scene-enriched.json")
    ap.add_argument("--report", default=None, help="JSON report path (default: next to --out)")
    ap.add_argument("--storey-m", type=float, default=STOREY_M)
    ap.add_argument("--dtm-tiles", default=None, help="if given, compare UrbIS ground Z with the DTM at each solid's centroid")
    a = ap.parse_args()
    import urbis3d
    scene = json.load(open(a.scene))
    frame = Frame(scene["area"])
    urb = urbis3d.read_buildings(a.gpkg)
    for u in urb:
        polys = [to_scene_polygon(r, frame) for r in u["footprint"]]
        u["poly"] = unary_union(polys)
    out, rep = join(scene, urb, a.storey_m)
    rep["urbis_edition"] = os.path.basename(a.gpkg)
    if a.dtm_tiles:
        from make_elevation import mosaic
        big, x0, y1, sx, sy = mosaic(a.dtm_tiles)
        diffs = []
        for u in urb:
            xs = [p[0] for r in u["footprint"] for p in r]; ys = [p[1] for r in u["footprint"] for p in r]
            c, r = int((sum(xs) / len(xs) - x0) / sx), int((y1 - sum(ys) / len(ys)) / sy)
            if 0 <= r < big.shape[0] and 0 <= c < big.shape[1] and np.isfinite(big[r, c]):
                diffs.append(u["ground_z"] - big[r, c])
        d = np.array(diffs)
        rep["ground_z_vs_dtm"] = {"n": len(d), "median_m": float(np.median(d)), "p5_m": float(np.percentile(d, 5)), "p95_m": float(np.percentile(d, 95)),
                                  "abs_p95_m": float(np.percentile(np.abs(d), 95)), "share_within_1m": float(np.mean(np.abs(d) <= 1))}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), separators=(",", ":"))
    json.dump(rep, open(a.report or os.path.splitext(a.out)[0] + "-report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
