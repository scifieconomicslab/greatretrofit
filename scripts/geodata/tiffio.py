"""Minimal TIFF reader/writer for the two files this folder handles.

read_tiled_float(): the GeoServer WCS GeoTIFF (tiled or stripped, 32/64-bit float, uncompressed or Deflate, big or little endian, with the
ModelTransformation tag 34264 or ModelPixelScale + ModelTiepoint), which Pillow cannot open (64-bit float).
write_geotiff_f32_lonlat(): a single-band float32 GeoTIFF in EPSG:4326, which `paperdolls ingest --elevation` reads.
"""
import struct
import zlib

import numpy as np

_TSIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 16: 8}
_TFMT = {1: "B", 2: "c", 3: "H", 4: "I", 6: "b", 7: "B", 8: "h", 9: "i", 11: "f", 12: "d", 16: "Q"}


def _ifd(b):
    bo = "<" if b[:2] == b"II" else ">"
    off = struct.unpack(bo + "I", b[4:8])[0]
    n = struct.unpack(bo + "H", b[off:off + 2])[0]
    tags = {}
    for i in range(n):
        tag, typ, cnt, val = struct.unpack(bo + "HHI4s", b[off + 2 + 12 * i:off + 14 + 12 * i])
        sz = _TSIZE.get(typ, 1) * cnt
        raw = b[struct.unpack(bo + "I", val)[0]:][:sz] if sz > 4 else val[:sz]
        if typ in _TFMT and typ != 2:
            tags[tag] = struct.unpack(bo + f"{cnt}{_TFMT[typ]}", raw)
        else:
            tags[tag] = raw
    return bo, tags


def read_tiled_float(path):
    """-> (array float64 rows north to south, x_west_edge, y_north_edge, cell_x, cell_y); NaN stays NaN."""
    b = open(path, "rb").read()
    bo, t = _ifd(b)
    w, h, bits = t[256][0], t[257][0], t[258][0]
    comp = t.get(259, (1,))[0]
    if t.get(339, (1,))[0] != 3 or bits not in (32, 64):
        raise ValueError(f"{path}: expected float samples, got format {t.get(339)} bits {bits}")
    if t.get(317, (1,))[0] != 1:
        raise ValueError(f"{path}: TIFF predictor {t.get(317)} not supported")
    dt = np.dtype(("<" if bo == "<" else ">") + ("f8" if bits == 64 else "f4"))
    out = np.full((h, w), np.nan)
    if 322 in t:                                                     # tiled
        tw, th = t[322][0], t[323][0]
        offs, cnts = t[324], t[325]
        across = (w + tw - 1) // tw
        for k, (o, c) in enumerate(zip(offs, cnts)):
            raw = b[o:o + c]
            if comp in (8, 32946):
                raw = zlib.decompress(raw)
            elif comp != 1:
                raise ValueError(f"{path}: compression {comp} not supported")
            tile = np.frombuffer(raw, dtype=dt).reshape(th, tw)
            r0, c0 = (k // across) * th, (k % across) * tw
            out[r0:r0 + th, c0:c0 + tw] = tile[:min(th, h - r0), :min(tw, w - c0)]
    else:                                                            # stripped
        rps = t.get(278, (h,))[0]
        for k, (o, c) in enumerate(zip(t[273], t[279])):
            raw = b[o:o + c]
            if comp in (8, 32946):
                raw = zlib.decompress(raw)
            elif comp != 1:
                raise ValueError(f"{path}: compression {comp} not supported")
            r0 = k * rps
            rows = min(rps, h - r0)
            out[r0:r0 + rows] = np.frombuffer(raw, dtype=dt)[:rows * w].reshape(rows, w)
    if 34264 in t:
        m = t[34264]
        x0, y0, sx, sy = m[3], m[7], m[0], -m[5]
        if abs(m[1]) > 0 or abs(m[4]) > 0:
            raise ValueError(f"{path}: rotated raster")
    else:
        sx, sy = t[33550][0], t[33550][1]
        x0, y0 = t[33922][3], t[33922][4]
    return out, x0, y0, sx, sy


def write_geotiff_f32_lonlat(path, z, lon0, lat0, dlon, dlat, nodata=-9999.0):
    """z: float array rows north to south; (lon0, lat0) = top-left *corner*; cell sizes in degrees. EPSG:4326, PixelIsArea."""
    from PIL import Image, TiffImagePlugin
    arr = np.where(np.isfinite(z), z, nodata).astype(np.float32)
    im = Image.fromarray(arr, mode="F")
    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    def put(tag, typ, val):
        ifd.tagtype[tag] = typ
        ifd[tag] = val
    put(33550, 12, (dlon, dlat, 0.0))
    put(33922, 12, (0.0, 0.0, 0.0, lon0, lat0, 0.0))
    put(34735, 3, (1, 1, 0, 3, 1024, 0, 1, 2, 1025, 0, 1, 1, 2048, 0, 1, 4326))
    put(42113, 2, f"{nodata:g}")
    im.save(path, tiffinfo=ifd, compression="tiff_deflate")
