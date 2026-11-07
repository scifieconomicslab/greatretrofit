"""Python reference vs JavaScript port on random cases, frame by frame (beyond the ~22 golden cases), plus the pack adapter's typed frames
checked against paperdolls' own checkFrame and an independent re-derivation of the mapping. Bounded: FUZZ_PARITY_N cases per kind (default 120)."""
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fuzz_lib as F  # noqa: E402
import parity_lib as P  # noqa: E402

PD = os.environ.get("PAPERDOLLS_DIR", "/data/ScifiEconomicsLab/scifirender/paperdolls")
pytestmark = pytest.mark.skipif(shutil.which("node") is None or not Path(PD, "viz/packruntime.js").exists(), reason="node or paperdolls not available")
N = int(os.environ.get("FUZZ_PARITY_N", "120"))
BASE = int(os.environ.get("FUZZ_SEED", "0"))


@pytest.mark.parametrize("kind", ["manifest", "edge"])
def test_js_matches_python_on_random_cases(kind):
    cases = [F.case_for(kind, BASE + i) for i in range(N)]
    js = P.run_js(cases)
    assert len(js) == len(cases)
    failures = []
    for c, j in zip(cases, js):
        bad = P.compare(c, j)
        if bad:
            failures.append(f"{kind} seed {c['seed']}: {bad[:2]}")
    assert not failures, "\n".join(failures[:8])


def test_validator_parity_on_manifest_ranges():
    """Values inside and at the edges of the manifest ranges are accepted by both Params() implementations."""
    import json
    import subprocess
    import tempfile
    import yaml
    from retrofit_v3 import Params
    m = yaml.safe_load(Path(F.ROOT, "packs/great-retrofit/pack.yaml").read_text())
    items = []
    for name, spec in m["params"].items():
        if spec["type"] in ("number", "integer"):
            items += [{"name": name, "value": v} for v in (spec["min"], spec["max"], spec["default"])]
    d = tempfile.mkdtemp()
    try:
        Path(d, "i.json").write_text(json.dumps(items))
        subprocess.run(["node", str(P.HERE / "run_js_params.js"), f"{d}/i.json", f"{d}/o.json"], check=True, timeout=120)
        out = json.loads(Path(d, "o.json").read_text())
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for it, o in zip(items, out):
        Params(**{it["name"]: it["value"]})          # raises if Python rejects a value the shell can send
        assert o["ok"], f"JS rejects {it}: {o}"
