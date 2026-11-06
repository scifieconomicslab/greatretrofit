"""Read the UrbIS 3D Buildings GeoPackage (Brussels, LoD2, EPSG:31370) with sqlite3 + struct only, and reduce each building solid to
a footprint and a few heights.

Layer ``BuildingFaces`` holds one row per face: ``BUSOLID_ID`` (the building solid), ``INSPIRE_ID`` (the *face* id, not the building's),
``TYPE`` (GROUNDSURFACE, ROOFSURFACE, WALLSURFACE, OUTERCEILING, OUTERFLOOR, OTHER) and a MultiPolygon Z geometry.
Per solid we take:
  footprint   the exterior ring(s) of its GROUNDSURFACE face(s), XY only
  ground_z    mean Z of the ground-surface vertices
  ridge_h     max Z over roof faces, minus ground_z
  eave_h      area-weighted 20th percentile of the roof faces' mean Z, minus ground_z  (about the eaves on a pitched roof, the roof level on a flat one)
  roof_area   total projected roof area
"""
import math
import sqlite3
import struct


def _parse_wkb(buf, off, out):
    """Parse one WKB geometry starting at ``off``; append polygons (list of rings of (x, y, z)) to ``out``; return new offset."""
    bo = "<" if buf[off] == 1 else ">"
    typ = struct.unpack_from(bo + "I", buf, off + 1)[0]
    off += 5
    base = typ % 1000 if typ < 4000 else typ & 0xFF
    dim3 = (typ // 1000 in (1, 3)) or bool(typ & 0x80000000)
    nd = 3 if dim3 else 2
    if base in (6, 7):  # MultiPolygon / GeometryCollection
        n = struct.unpack_from(bo + "I", buf, off)[0]
        off += 4
        for _ in range(n):
            off = _parse_wkb(buf, off, out)
        return off
    if base == 3:
        nr = struct.unpack_from(bo + "I", buf, off)[0]
        off += 4
        rings = []
        for _ in range(nr):
            npt = struct.unpack_from(bo + "I", buf, off)[0]
            off += 4
            vals = struct.unpack_from(bo + f"{npt * nd}d", buf, off)
            off += 8 * npt * nd
            rings.append([(vals[i], vals[i + 1], vals[i + 2] if nd == 3 else 0.0) for i in range(0, npt * nd, nd)])
        out.append(rings)
        return off
    raise ValueError(f"unsupported WKB geometry type {typ}")


def parse_gpkg_geometry(blob):
    """GeoPackage geometry blob -> list of polygons, each a list of rings of (x, y, z)."""
    if blob[:2] != b"GP":
        raise ValueError("not a GeoPackage geometry blob")
    flags = blob[3]
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]
    out = []
    _parse_wkb(blob, 8 + env, out)
    return out


def ring_area(ring):
    s = 0.0
    for i in range(len(ring) - 1):
        s += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return s / 2.0


def weighted_quantile(vals, weights, q):
    pairs = sorted(zip(vals, weights))
    tot = sum(w for _, w in pairs)
    if tot <= 0:
        return pairs[0][0] if pairs else float("nan")
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= q * tot:
            return v
    return pairs[-1][0]


def read_buildings(path, bbox=None):
    """-> list of dicts {id, footprint (list of XY rings, EPSG:31370), ground_z, ridge_h, eave_h, roof_area, n_faces}."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    solids = {}
    for sid, typ, blob in con.execute("select BUSOLID_ID, TYPE, geom from BuildingFaces"):
        s = solids.setdefault(sid, {"ground": [], "roof": [], "n": 0})
        s["n"] += 1
        if typ not in ("GROUNDSURFACE", "ROOFSURFACE"):
            continue
        for rings in parse_gpkg_geometry(blob):
            if typ == "GROUNDSURFACE":
                s["ground"].append(rings)
            else:
                ext = rings[0]
                a = abs(ring_area(ext))
                s["roof"].append((a, sum(p[2] for p in ext[:-1]) / max(1, len(ext) - 1), max(p[2] for p in ext)))
    out = []
    for sid, s in solids.items():
        if not s["ground"]:
            continue
        fp = [[(p[0], p[1]) for p in rings[0]] for rings in s["ground"]]
        gz = [p[2] for rings in s["ground"] for p in rings[0]]
        ground_z = sum(gz) / len(gz)
        d = {"id": sid.rsplit("/", 1)[-1], "footprint": fp, "ground_z": ground_z, "n_faces": s["n"], "roof_area": 0.0, "ridge_h": None, "eave_h": None}
        if s["roof"]:
            d["roof_area"] = sum(r[0] for r in s["roof"])
            d["ridge_h"] = max(r[2] for r in s["roof"]) - ground_z
            d["eave_h"] = weighted_quantile([r[1] for r in s["roof"]], [r[0] for r in s["roof"]], 0.2) - ground_z
        out.append(d)
    return out
