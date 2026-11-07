"""Random lifecycle programs on the JS pack runtime (start / step / run / setParams-rerun / second handle / emulated snapshot)."""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fuzz_lib as F  # noqa: E402

HERE = Path(__file__).resolve().parent
PD = os.environ.get("PAPERDOLLS_DIR", "/data/ScifiEconomicsLab/scifirender/paperdolls")
pytestmark = pytest.mark.skipif(shutil.which("node") is None or not Path(PD, "viz/packruntime.js").exists(), reason="node or paperdolls not available")
N = int(os.environ.get("FUZZ_LIFECYCLE_N", "12"))
BASE = int(os.environ.get("FUZZ_SEED", "0"))


def program(i):
    r = random.Random(f"lifecycle:{BASE}:{i}")
    nb = r.choice([3, 8, 15])                      # entity counts are fixed for the life of a PackRuntime
    specs, seed = [], r.randint(0, 2 ** 31 - 1)    # one seed per program: the shell's setParams(rerun) restarts with the manifest's seed
    for _ in range(2):
        p = F.manifest_params(r)
        specs.append({"p": p, "seed": seed, "buildings": nb})
    ops = [{"op": "start", "i": 0}]
    for _ in range(r.randint(4, 10)):
        c = r.choice(["step", "step", "run", "setParams", "start", "other", "clone"])
        if c == "step":
            ops.append({"op": "step", "n": r.randint(1, 7)})
        elif c == "run":
            ops.append({"op": "run", "to": r.randint(0, 40)})
        elif c in ("setParams", "start"):
            ops.append({"op": c, "i": r.randint(0, 1)})
        elif c == "other":
            ops.append({"op": "other", "i": 1, "n": r.randint(1, 6)})
        else:
            ops.append({"op": "clone", "n": r.randint(0, 20)})
    return {"id": f"{BASE}:{i}", "params": specs, "ops": ops, "max_t": 40}


def test_lifecycle_programs():
    progs = [program(i) for i in range(N)]
    d = tempfile.mkdtemp(prefix="fuzz-lc-")
    try:
        pp, op = os.path.join(d, "p.json"), os.path.join(d, "o.json")
        Path(pp).write_text(json.dumps(progs))
        r = subprocess.run(["node", str(HERE / "lifecycle_fuzz.js"), pp, op], capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stderr[-2000:]
        problems = json.loads(Path(op).read_text())
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert not problems, "\n".join(problems[:10])
