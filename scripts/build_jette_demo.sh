#!/usr/bin/env bash
# Builds build/jette_retrofit.html: the Great Retrofit pack on the whole commune of Jette (one offline HTML file).
#   scripts/build_jette_demo.sh
# Env:
#   PAPERDOLLS_DIR  paperdolls checkout (default: ../scifirender/paperdolls next to this repo's parent; see below)
#   PYTHON          python with paperdolls' requirements (default: .venv/bin/python if present, else python3)
#   SCENE           an existing scene json; skips the Overpass fetch
# With no SCENE and no cache/jette-commune-scene.json it fetches the commune from the public Overpass service ONCE (one POST, no retries;
# cache/ is gitignored) and ingests it with paperdolls. Everything after that is offline.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PD=${PAPERDOLLS_DIR:-/data/ScifiEconomicsLab/scifirender/paperdolls}
[ -f "$PD/paperdolls/cli.py" ] || { echo "paperdolls not found at $PD (set PAPERDOLLS_DIR)" >&2; exit 1; }
PY=${PYTHON:-}
if [ -z "$PY" ]; then if [ -x "$ROOT/.venv/bin/python" ]; then PY=$ROOT/.venv/bin/python; else PY=python3; fi; fi
pd() { PYTHONPATH="$PD" "$PY" -m paperdolls "$@"; }
mkdir -p cache build

SCENE=${SCENE:-cache/jette-commune-scene.json}
if [ ! -f "$SCENE" ]; then
  echo "== fetching Jette (OSM relation 58258) from Overpass, once" >&2
  pd osm-fetch --relation 58258 --out cache/jette-commune-extract.json
  pd ingest cache/jette-commune-extract.json --boundary-relation 58258 --out "$SCENE" --name Jette
fi

echo "== bundling the pack (prng + hook + runtime + bind -> one entry)" >&2
node packs/great-retrofit/tools/bundle.js
echo "== pack check" >&2
pd pack check packs/great-retrofit
pd pack check packs/great-retrofit/dist
echo "== pack build" >&2
pd pack build packs/great-retrofit/dist --scene "$SCENE" --out build/jette_retrofit.html
ls -l build/jette_retrofit.html
echo "Open build/jette_retrofit.html (file:// works). Browser checks: node scripts/verify_jette_browser.mjs" >&2
