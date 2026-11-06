"""Parity of the Python reference model and the JavaScript port (packs/great-retrofit/runtime.js).

Golden trajectories live in tests/golden/ and come from Python (tools/regen_golden.py). This file checks
  1. Python still reproduces them (so a model change must come with regenerated goldens), and
  2. the JS runtime reproduces them, by running tests/test_parity.js under node (skipped if node is absent).
Exact for integers and states, tolerance 1e-9 for floats. Run:  pytest packs/great-retrofit/tests
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import golden_lib as g  # noqa: E402

CASES = g.load_cases()


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
def test_python_matches_golden(case):
    want = json.loads((g.GOLDEN / f"{case['name']}.json").read_text())
    got = json.loads(json.dumps(g.case_output(case)))
    assert g.diff(want, got) is None, g.diff(want, got)


def test_scene_tables_match_golden():
    want = json.loads((g.GOLDEN / "scene_tables.json").read_text())
    got = {c["name"]: g.scene_output(c) for c in CASES["scene_table_cases"]}
    assert g.diff(want, json.loads(json.dumps(got))) is None


def test_cases_cover_every_mode_and_credit_setting():
    ps = [c["params"] for c in CASES["cases"]]
    assert {p.get("delivery_mode", "rebate_market") for p in ps} == {"rebate_market", "passthrough", "public_service"}
    assert {p.get("credit_access", "income_tested") for p in ps} == {"income_tested", "open", "none"}
    assert any(p.get("means_test") for p in ps) and any(p.get("refundable") for p in ps)
    for c in CASES["cases"]:   # a case with no adoption proves little
        assert json.loads((g.GOLDEN / f"{c['name']}.json").read_text())["events"], c["name"]


def test_cases_cover_new_mechanisms_both_ways():
    ps = {c["name"]: c["params"] for c in CASES["cases"]}
    flags = lambda key, default: {p.get(key, default) for p in ps.values()}   # noqa: E731
    assert flags("peer_effect", True) == {True, False} and flags("shared_measure", True) == {True, False}
    assert flags("means_test", False) == {True, False}
    assert flags("energy_scenario", "rising") == {"flat", "rising", "shock"}
    assert {"vote_threshold" in p and p["vote_threshold"] for p in ps.values()} >= {1.0, 0.6666666666666666}
    assert flags("canvass_target_hours", 2.0) >= {0.0, 6.0, 2.0}
    assert any(p.get("means_test") and p.get("delivery_mode", "rebate_market") == "rebate_market" for p in ps.values())
    for name in ("shared_vote_100_passthrough_s12", "shared_vote_twothirds_passthrough_s12", "shared_vote_rebate_open_credit_s13",
                 "shared_public_service_capacity_s14"):
        assert json.loads((g.GOLDEN / f"{name}.json").read_text())["votes"], name


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_golden():
    r = subprocess.run(["node", str(Path(__file__).with_name("test_parity.js"))], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
