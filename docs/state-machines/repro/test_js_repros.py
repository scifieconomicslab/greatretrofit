"""Runs the node scripts in js/. lifecycle_surface.js documents the handle lifecycle (SM-11 to SM-13); the scripts for the fixed defects (SM-1, SM-7 to SM-10)
became regression tests under tests/model/.
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_js_repros.py -q"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent / "js"
PD = os.environ.get("PAPERDOLLS_DIR", "/data/ScifiEconomicsLab/scifirender/paperdolls")
pytestmark = pytest.mark.skipif(shutil.which("node") is None or not Path(PD, "viz/packruntime.js").exists(), reason="node or paperdolls not available")


def _run(name):
    return subprocess.run(["node", str(HERE / name)], capture_output=True, text=True, timeout=120)


def test_lifecycle_surface_script_runs():
    r = _run("lifecycle_surface.js")
    print(r.stdout)
    assert r.returncode == 0, r.stderr
