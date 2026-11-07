"""Runs the node repro scripts in js/. A script exits 1 while its bug is present (expected today, hence xfail strict) and 0 once fixed.
Run:  PYTHONPATH=v3/src .venv/bin/python -m pytest docs/state-machines/repro/test_js_repros.py -q"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent / "js"
PD = os.environ.get("PAPERDOLLS_DIR", "/data/ScifiEconomicsLab/scifirender/paperdolls")
pytestmark = pytest.mark.skipif(shutil.which("node") is None or not Path(PD, "viz/packruntime.js").exists(), reason="node or paperdolls not available")

BUGS = {
    "params_coercion.js": "SM-10: JS Params accepts null, numeric strings and arrays",
}


def _run(name):
    return subprocess.run(["node", str(HERE / name)], capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("name", sorted(BUGS))
def test_bug_script(name):
    r = _run(name)
    print(r.stdout)
    if r.returncode == 0:
        return                    # fixed
    pytest.xfail(BUGS[name]) if "BUG PRESENT" in r.stdout else pytest.fail(r.stdout + r.stderr)


def test_lifecycle_surface_script_runs():
    r = _run("lifecycle_surface.js")
    print(r.stdout)
    assert r.returncode == 0, r.stderr
