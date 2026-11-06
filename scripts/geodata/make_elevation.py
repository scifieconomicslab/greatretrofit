#!/usr/bin/env python3
"""Build the elevation input for `paperdolls ingest --elevation` from the Brussels UrbIS DTM tiles (see fetch_dtm.py).

CRS handling
  * The DTM tiles are EPSG:31370 (Belgian Lambert 72), 1 m cells, heights in metres (TAW/DNG vertical datum, not converted).
  * paperdolls' elevation reader refuses anything but lon/lat degrees (EPSG:4326/4258/4979) or Web Mercator, and takes the scene's
    local frame from the scene itself (ingest/geo.py LocalFrame: tangent plane at area.origin, x east, y south, rotated by area.rotation_deg).
    So the output is a plain EPSG:4326 float32 GeoTIFF; the rotation never enters the elevation file. The scene's `area` block is used here
    only to choose the extent: every scene building/road/tree point is turned into lon/lat with the same LocalFrame formulas (latlon()),
    padded by --margin, and the target grid covers that box.
  * For each target cell centre (lon, lat) we go to EPSG:31370 (scripts/geodata/lambert72.py, pure Python, agrees with PROJ to 2 mm) and read
    the 1 m DTM there. The DTM is first box-averaged over the cell size (so a 4 m cell is the mean of the 1 m cells, not an aliased sample)
    and then bilinearly interpolated. NoData cells (NaN) drop out.

    python3 scripts/geodata/make_elevation.py --scene cache/jette-commune-scene.json --tiles data/raw/dtm_wcs --out build/jette-elevation.tif
Needs numpy and Pillow. Writes the GeoTIFF and a small JSON summary next to it.
"""
import argparse, glob, json, math, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambert72 import lonlat_to_lambert72          # noqa: E402
from tiffio import read_tiled_float, write_geotiff_f32_lonlat   # noqa: E402

R_EARTH = 6371008.8
DEG = math.pi / 180.0


def frame_latlon(area):
    """The scene's LocalFrame.latlon(), re-implemented from paperdolls/ingest/geo.py (x east, y south, rotated by rotation_deg)."""
    lat0, lon0 = area["origin"]["lat"], area["origin"]["lon"]
    kx, ky = R_EARTH * math.cos(lat0 * DEG) * DEG, R_EARTH * DEG
    a = area.get("rotation_deg", 0.0) * DEG
    c, s = math.cos(a), math.sin(a)

    def latlon(xr, yr):
        x, y = xr * c - yr * s, xr * s + yr * c
        return lat0 - y / ky, lon0 + x / kx
    return latlon


def scene_points(scene):
    for b in scene.get("buildings", []):
        yield from b["footprint"]
    for r in scene.get("roads", []):
        yield from r["points"] if "points" in r else r.get("pts", [])
    for t in scene.get("trees", []):
        yield t[0], t[1]


def mosaic(tiles_dir):
    files = sorted(glob.glob(os.path.join(tiles_dir, "*.tif")))
    if not files:
        sys.exit(f"no .tif tiles in {tiles_dir}")
    parts = [read_tiled_float(f) for f in files]
    if len({(p[3], p[4]) for p in parts}) != 1:
        sys.exit("tiles have different cell sizes")
    sx, sy = parts[0][3], parts[0][4]
    x0 = min(p[1] for p in parts); y1 = max(p[2] for p in parts)
    x1 = max(p[1] + p[0].shape[1] * sx for p in parts); y0 = min(p[2] - p[0].shape[0] * sy for p in parts)
    W, H = int(round((x1 - x0) / sx)), int(round((y1 - y0) / sy))
    big = np.full((H, W), np.nan)
    for a, px, py, _, _ in parts:
        c0, r0 = int(round((px - x0) / sx)), int(round((y1 - py) / sy))
        big[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a
    # The service fills ground it has no data for (outside the Region: the north-west corner of this box, in Flanders) with exactly 0.0, not
    # NaN. Brussels lies 15 m or more above sea level, so an exact 0 is NoData here. (Checked: 2.6% of the box, one contiguous block.)
    big[big == 0.0] = np.nan
    return big, x0, y1, sx, sy


def box_mean(a, k):
    """Mean over k x k windows (NaN ignored), same shape; k odd or even, centred approximately."""
    if k <= 1:
        return a
    ok = np.isfinite(a)
    v = np.where(ok, a, 0.0)
    def csum(m):
        c = np.pad(m, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        return c
    h = k // 2
    H, W = a.shape
    cv, cn = csum(v), csum(ok.astype(float))
    r0 = np.clip(np.arange(H) - h, 0, H); r1 = np.clip(np.arange(H) - h + k, 0, H)
    c0 = np.clip(np.arange(W) - h, 0, W); c1 = np.clip(np.arange(W) - h + k, 0, W)
    s = cv[np.ix_(r1, c1)] - cv[np.ix_(r0, c1)] - cv[np.ix_(r1, c0)] + cv[np.ix_(r0, c0)]
    n = cn[np.ix_(r1, c1)] - cn[np.ix_(r0, c1)] - cn[np.ix_(r1, c0)] + cn[np.ix_(r0, c0)]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, s / n, np.nan)


def bilinear(a, fx, fy):
    """a: 2D with NaN; fx, fy: fractional cell-centre coordinates (column, row). NaN corners are re-weighted away; outside -> NaN."""
    H, W = a.shape
    out = np.full(fx.shape, np.nan)
    inside = (fx >= 0) & (fy >= 0) & (fx <= W - 1) & (fy <= H - 1)
    x, y = fx[inside], fy[inside]
    i = np.minimum(np.floor(x).astype(int), W - 2); j = np.minimum(np.floor(y).astype(int), H - 2)
    u, v = x - i, y - j
    num = np.zeros_like(x); den = np.zeros_like(x)
    for di, dj, w in ((0, 0, (1 - u) * (1 - v)), (1, 0, u * (1 - v)), (0, 1, (1 - u) * v), (1, 1, u * v)):
        q = a[j + dj, i + di]
        g = np.isfinite(q)
        num += np.where(g, q * w, 0.0); den += np.where(g, w, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[inside] = np.where(den > 1e-9, num / den, np.nan)
    return out


def build(scene, tiles_dir, cell_m, margin_m):
    area = scene["area"]
    latlon = frame_latlon(area)
    pts = np.array(list(scene_points(scene)), dtype=float)
    xmin, ymin = pts.min(0) - margin_m
    xmax, ymax = pts.max(0) + margin_m
    corners = [latlon(x, y) for x in (xmin, xmax) for y in (ymin, ymax)]
    lat_hi, lat_lo = max(c[0] for c in corners), min(c[0] for c in corners)
    lon_lo, lon_hi = min(c[1] for c in corners), max(c[1] for c in corners)
    lat_mid = (lat_hi + lat_lo) / 2
    dlat = cell_m / (R_EARTH * DEG)
    dlon = cell_m / (R_EARTH * DEG * math.cos(lat_mid * DEG))
    nx, ny = int(math.ceil((lon_hi - lon_lo) / dlon)), int(math.ceil((lat_hi - lat_lo) / dlat))
    big, x0, y1, sx, sy = mosaic(tiles_dir)
    sm = box_mean(big, int(round(cell_m / sx)))
    lons = lon_lo + (np.arange(nx) + 0.5) * dlon
    lats = lat_hi - (np.arange(ny) + 0.5) * dlat
    X = np.empty((ny, nx)); Y = np.empty((ny, nx))
    for j, la in enumerate(lats):
        for i, lo in enumerate(lons):
            X[j, i], Y[j, i] = lonlat_to_lambert72(lo, la)
    # fractional cell-centre index in the mosaic (cell (c, r) has its centre at x0 + (c + .5) sx, y1 - (r + .5) sy)
    z = bilinear(sm, (X - x0) / sx - 0.5, (y1 - Y) / sy - 0.5)
    info = {"grid": [nx, ny], "cell_m": cell_m, "lon0_corner": lon_lo, "lat0_corner": lat_hi, "dlon": dlon, "dlat": dlat,
            "z_min": float(np.nanmin(z)), "z_max": float(np.nanmax(z)), "z_mean": float(np.nanmean(z)),
            "nodata_share": float(np.mean(~np.isfinite(z))),
            "source_mosaic": {"shape": list(big.shape), "nodata_share": float(np.mean(~np.isfinite(big))),
                              "lambert_x0": x0, "lambert_y1": y1, "cell_m": sx}}
    return z, lon_lo, lat_hi, dlon, dlat, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", default="cache/jette-commune-scene.json")
    ap.add_argument("--tiles", default="data/raw/dtm_wcs")
    ap.add_argument("--out", default="build/jette-elevation.tif")
    ap.add_argument("--cell-m", type=float, default=4.0, help="output cell in metres (default 4)")
    ap.add_argument("--margin", type=float, default=60.0, help="metres added around the scene extent (default 60)")
    a = ap.parse_args()
    scene = json.load(open(a.scene))
    z, lon0, lat0, dlon, dlat, info = build(scene, a.tiles, a.cell_m, a.margin)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    write_geotiff_f32_lonlat(a.out, z, lon0, lat0, dlon, dlat)
    info["scene_area"] = scene["area"]
    json.dump(info, open(os.path.splitext(a.out)[0] + ".json", "w"), indent=1)
    print(json.dumps({k: v for k, v in info.items() if k != "scene_area"}, indent=1))
    print("wrote", a.out, os.path.getsize(a.out) // 1024, "KiB")


if __name__ == "__main__":
    main()
