"""Runs the node tests for bind.js (skipped if node is absent)."""
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_bind_js():
    r = subprocess.run(["node", str(Path(__file__).with_name("test_bind.js"))], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
