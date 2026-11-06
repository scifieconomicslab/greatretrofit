#!/usr/bin/env bash
# Builds build/jette-scene-enriched.json: the Jette scene with real ground heights (UrbIS DTM) and real building heights (UrbIS 3D).
#   scripts/geodata/build_enriched.sh
# Env: PAPERDOLLS_DIR, PYTHON (as scripts/build_jette_demo.sh; the python needs numpy, Pillow, pyyaml, shapely).
# Steps (each skipped when its output exists; delete the file to redo):
#   1. fetch the 1 m DTM tiles (WCS, ~58 MB) and the Jette UrbIS 3D GeoPackage (~17 MB) into data/raw/  (public, open data; see docs/calibration/geodata-acquired.md)
#   2. make_elevation.py -> build/jette-elevation.tif (EPSG:4326 float32 GeoTIFF)
#   3. paperdolls ingest <extract> --elevation ... -> build/jette-scene-terrain.json  (the OSM extract cache/jette-commune-extract.json must exist;
#      it is fetched once from Overpass if missing)
#   4. join_heights.py -> build/jette-scene-enriched.json (+ -report.json)
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
PD=${PAPERDOLLS_DIR:-/data/ScifiEconomicsLab/scifirender/paperdolls}
PY=${PYTHON:-}
if [ -z "$PY" ]; then if [ -x "$ROOT/.venv/bin/python" ]; then PY=$ROOT/.venv/bin/python; else PY=python3; fi; fi
mkdir -p cache build data/raw
GPKG=data/raw/urbis3d/x/gpkg/UrbISBuildings3D_21010.gpkg
if [ ! -d data/raw/dtm_wcs ] || [ -z "$(ls data/raw/dtm_wcs/*.tif 2>/dev/null)" ]; then "$PY" scripts/geodata/fetch_dtm.py; fi
if [ ! -f "$GPKG" ]; then
  mkdir -p data/raw/urbis3d/x
  curl -fsS -o data/raw/urbis3d/jette3d.zip https://urbisdownload.datastore.brussels/UrbIS/Vector/M8/UrbIS-Buildings3D/GPKG/UrbISBuildings3D_31370_GPKG_21010_20261003.zip
  unzip -o -q data/raw/urbis3d/jette3d.zip -d data/raw/urbis3d/x
fi
if [ ! -f cache/jette-commune-extract.json ]; then
  PYTHONPATH="$PD" "$PY" -m paperdolls osm-fetch --relation 58258 --out cache/jette-commune-extract.json
fi
# make_elevation needs a scene only for its area/extent: the flat scene is made from the same extract
if [ ! -f cache/jette-commune-scene.json ]; then
  PYTHONPATH="$PD" "$PY" -m paperdolls ingest cache/jette-commune-extract.json --boundary-relation 58258 --out cache/jette-commune-scene.json --name Jette
fi
[ -f build/jette-elevation.tif ] || "$PY" -I scripts/geodata/make_elevation.py --scene cache/jette-commune-scene.json --out build/jette-elevation.tif
[ -f build/jette-scene-terrain.json ] || PYTHONPATH="$PD" "$PY" -m paperdolls ingest cache/jette-commune-extract.json --boundary-relation 58258 \
    --elevation build/jette-elevation.tif --out build/jette-scene-terrain.json --name Jette
"$PY" -I scripts/geodata/join_heights.py --scene build/jette-scene-terrain.json --gpkg "$GPKG" --out build/jette-scene-enriched.json --dtm-tiles data/raw/dtm_wcs > /dev/null
echo "wrote build/jette-scene-enriched.json (report: build/jette-scene-enriched-report.json)" >&2
