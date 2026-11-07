"""Run a node script from tests/model and return its JSON output."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def run_node(script, *args):
    r = subprocess.run(["node", str(HERE / script), *map(str, args)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)
