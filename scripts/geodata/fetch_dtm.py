#!/usr/bin/env python3
"""Download the Brussels UrbIS DTM (1 m) for Jette from the Region's public WCS, in 1 km tiles.

Service: https://geoservices-grid.irisnet.be/geoserver/urbisgrid/ows  (WCS 2.0.1, coverage urbisgrid__DTM, EPSG:31370, 1 m cells,
no key or registration). Licence per the Geobru record 99e17c00-6b3a-11ed-aa8d-010101010000: CC0 with an "other restrictions" note
(see docs/calibration/geodata-acquired.md). Raw tiles go to data/raw/dtm_wcs/ (gitignored). Existing tiles are not fetched again.
Politeness: one request at a time, a pause between requests, up to three attempts per tile with a growing wait.

    python3 scripts/geodata/fetch_dtm.py [--out data/raw/dtm_wcs] [--bbox X0 Y0 X1 Y1]
Default bbox (EPSG:31370) covers the cached Jette commune scene with a margin: 144900 172600 148200 176100.
"""
import argparse, hashlib, json, os, sys, time, urllib.error, urllib.request

URL = ("https://geoservices-grid.irisnet.be/geoserver/urbisgrid/ows?service=WCS&version=2.0.1&request=GetCoverage"
       "&coverageId=urbisgrid__DTM&format=image/tiff&geotiff:compression=Deflate&subset=X({x0},{x1})&subset=Y({y0},{y1})")
UA = "TheGreatRetrofit-geodata/0.1 (research; one-off tile download)"


def tiles(bbox, size=1000):
    x0, y0, x1, y1 = bbox
    xs = list(range(x0, x1, size)); ys = list(range(y0, y1, size))
    return [(x, y, min(x + size, x1), min(y + size, y1)) for y in ys for x in xs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/dtm_wcs")
    ap.add_argument("--bbox", nargs=4, type=int, default=[144900, 172600, 148200, 176100])
    ap.add_argument("--pause", type=float, default=3.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for (x0, y0, x1, y1) in tiles(a.bbox):
        fn = os.path.join(a.out, f"dtm_{x0}_{y0}_{x1}_{y1}.tif")
        if not os.path.exists(fn):
            req = urllib.request.Request(URL.format(x0=x0, x1=x1, y0=y0, y1=y1), headers={"User-Agent": UA})
            for attempt in (1, 2, 3):                      # the service sometimes answers 500 once; wait and ask again
                try:
                    with urllib.request.urlopen(req, timeout=180) as r:
                        data = r.read()
                    break
                except urllib.error.HTTPError as e:
                    print(f"{fn}: HTTP {e.code} (attempt {attempt})", file=sys.stderr)
                    if attempt == 3:
                        raise
                    time.sleep(15 * attempt)
            if data[:2] not in (b"MM", b"II"):
                sys.exit(f"{fn}: not a TIFF: {data[:200]!r}")
            open(fn, "wb").write(data)
            time.sleep(a.pause)
        b = open(fn, "rb").read()
        rows.append({"file": os.path.basename(fn), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
        print(rows[-1], file=sys.stderr)
    json.dump({"fetched": time.strftime("%Y-%m-%d"), "tiles": rows}, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print("total MB", sum(r["bytes"] for r in rows) / 1e6)


if __name__ == "__main__":
    main()
