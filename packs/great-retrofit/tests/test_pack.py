"""The pack manifest: valid, consistent with the Python model's defaults, and its runtime passes the paperdolls pack checks.

Validation uses the paperdolls validator when it can be found (env PAPERDOLLS_DIR, or the sibling checkout of branch
claude/model-packs-6a7453), else the JSON Schema copy in tests/fixtures (needs `jsonschema`), else the test is skipped.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
yaml = pytest.importorskip("yaml")

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
sys.path.insert(0, str(PACK / "tools"))
import golden_lib as g  # noqa: E402

MANIFEST = yaml.safe_load((PACK / "pack.yaml").read_text())
PD_CANDIDATES = [os.environ.get("PAPERDOLLS_DIR", ""),
                 "/data/ScifiEconomicsLab/scifirender/paperdolls"]


def paperdolls_dir():
    for d in PD_CANDIDATES:
        if d and (Path(d) / "paperdolls" / "pack.py").is_file() and (Path(d) / "viz" / "packvalidate.js").is_file():
            return Path(d)
    return None


def test_manifest_validates_with_paperdolls_validator():
    pd = paperdolls_dir()
    if pd is None:
        pytest.skip("paperdolls checkout with the pack validator not found (set PAPERDOLLS_DIR)")
    code = ("import sys, json; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]);"
            "from paperdolls import pack; e, w = pack.check(sys.argv[2]); print(json.dumps({'errors': e, 'warnings': w}))")
    r = subprocess.run([sys.executable, "-c", code, str(pd), str(PACK)], capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["errors"] == [], res["errors"]


def test_manifest_validates_against_schema_copy():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((HERE / "fixtures" / "pack.schema.json").read_text())
    jsonschema.validate(MANIFEST, schema)


def test_banner_states_geometry_real_households_synthetic_numbers_placeholder():
    b = MANIFEST["banner"].lower()
    assert "openstreetmap" in b and "synthetic" in b and "placeholder" in b


def test_param_defaults_match_python_params():
    from retrofit_v3 import Params
    base = Params()
    for name, spec in MANIFEST["params"].items():
        assert getattr(base, name) == spec["default"], name
        if spec["type"] in ("number", "integer"):
            assert spec["min"] <= spec["default"] <= spec["max"], name
    assert MANIFEST["time"]["steps"] == base.horizon_months


def test_presets_and_param_values_construct_valid_params():
    from retrofit_v3 import Params
    for p in MANIFEST["presets"]:
        Params(**p["params"])
    for name, spec in MANIFEST["params"].items():
        if spec["type"] == "enum":
            for v in spec["values"]:
                Params(**{name: v["value"] if isinstance(v, dict) else v})
        elif spec["type"] in ("number", "integer"):
            Params(**{name: spec["min"]}), Params(**{name: spec["max"]})


def test_entity_fields_match_frame_schema():
    from retrofit_v3.frames import BuildingFrame, BUILDING_STATES
    from retrofit_v3.entities import TENURES
    f = MANIFEST["entities"]["building"]["fields"]
    derived = {"units_done", "cannot_front"}   # computed by the pack adapter from adopted_share * units and units_cannot_front
    assert set(f) - derived <= set(BuildingFrame.__annotations__)
    assert tuple(f["state"]["values"]) == BUILDING_STATES and tuple(f["tenure"]["values"]) == TENURES
    keys = {"adoption_by_quintile", "rebate_per_euro", "can_front_cost", "cost_per_retrofit", "public_cost", "bills_saved"}
    assert keys <= set(MANIFEST["series"])


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_runtime_passes_paperdolls_runtime_checks(tmp_path):
    pd = paperdolls_dir()
    if pd is None:
        pytest.skip("paperdolls checkout not found (set PAPERDOLLS_DIR)")
    mj = tmp_path / "manifest.json"
    mj.write_text(json.dumps(MANIFEST))
    r = subprocess.run(["node", str(HERE / "pack_runtime_check.js"), str(pd), str(mj)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
