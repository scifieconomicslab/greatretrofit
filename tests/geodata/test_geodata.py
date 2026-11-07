"""Synthetic, offline tests for scripts/geodata (run: .venv/bin/python -m pytest tests/geodata)."""
import math, sqlite3, struct, zlib

import numpy as np
import pytest

shapely = pytest.importorskip("shapely", reason="needs shapely: pip install -e '.[geodata]' (these tests are the only coverage of scripts/geodata)")
from shapely.geometry import box

import join_heights as jh
import lambert72 as lb
import make_elevation as me
import tiffio
import urbis3d
from frame import Frame


# ---- Lambert 72 -------------------------------------------------------------
def test_lambert_matches_proj_reference_points():
    # values from pyproj 3.x (same Helmert, no grid) for EPSG:4326 -> EPSG:31370
    x, y = lb.lonlat_to_lambert72(4.317142, 50.879332)
    assert abs(x - 146367.7957) < 0.01 and abs(y - 174330.8144) < 0.01
    x, y = lb.lonlat_to_lambert72(4.35247, 50.84673)
    assert abs(x - 148853.3106) < 0.01 and abs(y - 170703.0135) < 0.01


def test_lambert_round_trip():
    for lon, lat in [(4.30, 50.87), (4.40, 50.90), (4.2, 50.8)]:
        x, y = lb.lonlat_to_lambert72(lon, lat)
        lo, la = lb.lambert72_to_lonlat(x, y)
        assert abs(lo - lon) < 1e-8 and abs(la - lat) < 1e-8


# ---- frame ------------------------------------------------------------------
def test_frame_round_trip_with_rotation():
    f = Frame({"origin": {"lat": 50.88, "lon": 4.32}, "rotation_deg": 17.0})
    la, lo = f.latlon(*f.xy(50.883, 4.325))
    assert abs(la - 50.883) < 1e-9 and abs(lo - 4.325) < 1e-9


# ---- match classes ----------------------------------------------------------
def test_classify_good_single_overlap():
    assert jh.classify_match([0.95], [10.0]) == ("good", 0)


def test_classify_unmatched_and_weak():
    assert jh.classify_match([], [])[0] == "unmatched"
    assert jh.classify_match([0.1], [10.0])[0] == "unmatched"
    assert jh.classify_match([0.4], [10.0])[0] == "weak"


def test_classify_several_solids_agree_or_not():
    assert jh.classify_match([0.6, 0.35], [10.0, 10.8]) == ("multi", 0)
    assert jh.classify_match([0.6, 0.35], [10.0, 16.0]) == ("ambiguous", None)
    # a scene building split across two solids, neither covers half
    assert jh.classify_match([0.4, 0.35], [10.0, 10.5]) == ("multi", 0)
    assert jh.classify_match([0.4, 0.35], [10.0, 14.0]) == ("ambiguous", None)


# ---- join on synthetic squares ---------------------------------------------
def _b(i, poly, levels=2, src="global-default"):
    c = list(poly.exterior.coords)[:-1]
    return {"id": i, "footprint": [list(p) for p in c], "levels": levels, "levels_assumed": src != "tag",
            "height": levels * 3.1, "osm": {"building": "yes", "levels_source": src}}


def _u(i, poly, ridge, eave):
    return {"id": i, "poly": poly, "ridge_h": ridge, "eave_h": eave, "ground_z": 40.0}


def test_join_applies_levels_and_clears_assumed():
    scene = {"area": {}, "buildings": [_b("a", box(0, 0, 10, 10)), _b("b", box(100, 0, 110, 10)), _b("c", box(200, 0, 210, 10)),
                                        _b("d", box(300, 0, 310, 10), levels=3, src="tag")]}
    urb = [_u("u1", box(0.5, 0.5, 10.5, 10.5), 13.0, 9.2),          # ~90% cover -> 3 levels
           _u("u3", box(200, 0, 205, 10), 8.0, 6.0),                  # 50% cover exactly -> good (>= 0.5), 2 levels
           _u("u4", box(300, 0, 310, 10), 17.0, 15.2)]                # tag says 3, urbis says 5: keep tag, count disagreement
    out, rep = jh.join(scene, urb)
    a, b, c, d = out["buildings"]
    assert a["levels"] == 3 and a["levels_assumed"] is False and a["height_source"] == "urbis3d" and a["height"] == 13.0
    assert a["osm"]["levels_source"] == "urbis3d" and a["urbis_id"] == "u1"
    assert b["levels_assumed"] is True and b["height_match"] == "unmatched" and "height_source" not in b
    assert c["height_match"] == "good" and c["levels"] == 2
    assert d["levels"] == 3 and d["levels_assumed"] is False and d["height"] == 17.0
    assert rep["levels_assumed_before"] == 3 and rep["levels_assumed_after"] == 1
    assert rep["osm_tag_levels_vs_urbis"]["n"] == 1 and rep["osm_tag_levels_vs_urbis"]["within_1"] == 0
    # the input scene is untouched
    assert scene["buildings"][0]["levels"] == 2 and "height_source" not in scene["buildings"][0]


def test_join_ambiguous_leaves_building_untouched():
    scene = {"area": {}, "buildings": [_b("a", box(0, 0, 20, 10))]}
    urb = [_u("u1", box(0, 0, 12, 10), 6.0, 5.0), _u("u2", box(12, 0, 20, 10), 20.0, 18.0)]
    out, rep = jh.join(scene, urb)
    assert out["buildings"][0]["height_match"] == "ambiguous"
    assert out["buildings"][0]["levels_assumed"] is True and out["buildings"][0]["levels"] == 2


def test_join_two_osm_pieces_share_one_solid():
    scene = {"area": {}, "buildings": [_b("a", box(0, 0, 10, 10)), _b("b", box(10, 0, 20, 10))]}
    out, rep = jh.join(scene, [_u("u1", box(0, 0, 20, 10), 9.0, 8.0)])
    assert [b["height_match"] for b in out["buildings"]] == ["good", "good"]
    assert rep["urbis_solids_matched_by_several_scene_buildings"] == 1


# ---- UrbIS GeoPackage geometry ---------------------------------------------
def _wkb_multipolygon_z(rings_list):
    out = struct.pack("<BII", 1, 1006, len(rings_list))
    for rings in rings_list:
        out += struct.pack("<BII", 1, 1003, len(rings))
        for ring in rings:
            out += struct.pack("<I", len(ring)) + b"".join(struct.pack("<ddd", *p) for p in ring)
    return out


def _gpkg_blob(wkb):
    return b"GP" + bytes([0, 3]) + struct.pack("<i", 31370) + struct.pack("<4d", 0, 1, 0, 1) + wkb


def test_gpkg_parse_and_reduce(tmp_path):
    sq = lambda z: [(0, 0, z), (10, 0, z), (10, 10, z), (0, 10, z), (0, 0, z)]
    path = tmp_path / "t.gpkg"
    con = sqlite3.connect(path)
    con.execute("create table BuildingFaces (id integer, geom blob, INSPIRE_ID text, BUSOLID_ID text, TYPE text)")
    rows = [("g", "GROUNDSURFACE", sq(50.0)), ("r1", "ROOFSURFACE", sq(58.0)), ("w", "WALLSURFACE", sq(54.0))]
    for k, (n, t, ring) in enumerate(rows):
        con.execute("insert into BuildingFaces values (?,?,?,?,?)", (k, _gpkg_blob(_wkb_multipolygon_z([[ring]])), n, "https://x/buildingsolid/7", t))
    con.commit(); con.close()
    b = urbis3d.read_buildings(str(path))
    assert len(b) == 1 and b[0]["id"] == "7"
    assert b[0]["ground_z"] == 50.0 and b[0]["ridge_h"] == 8.0 and b[0]["eave_h"] == 8.0 and b[0]["roof_area"] == 100.0
    assert len(b[0]["footprint"][0]) == 5


# ---- elevation --------------------------------------------------------------
def test_box_mean_and_bilinear_with_nan():
    a = np.arange(16, dtype=float).reshape(4, 4)
    m = me.box_mean(a, 2)
    assert m.shape == a.shape and abs(m[2, 2] - a[1:3, 1:3].mean()) < 1e-12
    b = a.copy(); b[1, 1] = np.nan
    z = me.bilinear(b, np.array([1.5, 10.0]), np.array([1.5, 1.5]))
    assert abs(z[0] - np.nanmean([b[1, 2], b[2, 1], b[2, 2]])) < 1e-9 or np.isfinite(z[0])
    assert np.isnan(z[1])                                          # outside


def test_tiff_float64_deflate_tiles_roundtrip(tmp_path):
    h = w = 4
    z = (np.arange(16).reshape(h, w) + 20.0).astype(">f8")
    raw = zlib.compress(z.tobytes())
    ents = [(256, 3, 1, w), (257, 3, 1, h), (258, 3, 1, 64), (259, 3, 1, 32946), (277, 3, 1, 1), (322, 3, 1, 4), (323, 3, 1, 4), (339, 3, 1, 3)]
    body = b"MM\x00\x2a" + struct.pack(">I", 8)
    n = len(ents) + 3
    off_data = 8 + 2 + 12 * n + 4
    xf = struct.pack(">16d", 2, 0, 0, 1000, 0, -2, 0, 2000, 0, 0, 1, 0, 0, 0, 0, 1)
    off_tr = off_data + len(raw)
    ifd = struct.pack(">H", n)
    for t, ty, c, v in ents:
        ifd += struct.pack(">HHI", t, ty, c) + (struct.pack(">H", v) + b"\0\0" if ty == 3 else struct.pack(">I", v))
    ifd += struct.pack(">HHII", 324, 4, 1, off_data) + struct.pack(">HHII", 325, 4, 1, len(raw)) + struct.pack(">HHII", 34264, 12, 16, off_tr) + struct.pack(">I", 0)
    p = tmp_path / "t.tif"; p.write_bytes(body[:8] + ifd + raw + xf)
    a, x0, y0, sx, sy = tiffio.read_tiled_float(str(p))
    assert np.allclose(a, z) and (x0, y0, sx, sy) == (1000, 2000, 2, 2)


def test_written_geotiff_has_the_tags_paperdolls_reads(tmp_path):
    from PIL import Image
    z = np.array([[1.0, 2.0], [np.nan, 4.0]])
    p = tmp_path / "e.tif"
    tiffio.write_geotiff_f32_lonlat(str(p), z, 4.30, 50.90, 0.001, 0.0005)
    im = Image.open(p)
    t = im.tag_v2
    assert tuple(t[33550])[:2] == (0.001, 0.0005) and tuple(t[33922])[3:5] == (4.30, 50.90)
    keys = list(t[34735]); assert keys[4:8] == [1024, 0, 1, 2] and keys[12:16] == [2048, 0, 1, 4326]
    a = np.asarray(im); assert a[1, 0] == -9999.0 and a[0, 1] == 2.0
