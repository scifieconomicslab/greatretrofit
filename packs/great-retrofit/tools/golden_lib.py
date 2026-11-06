"""Shared by tools/regen_golden.py and tests/test_parity.py: build Python Params from a case, and compare frames."""
import json
import math
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
REPO = PACK.parents[1]
sys.path.insert(0, str(REPO / "v3" / "src"))

from retrofit_v3 import Params, run_simulation  # noqa: E402
from retrofit_v3.entities import BuildingSpec  # noqa: E402
from retrofit_v3.scene_entities import SceneRules, build_entities  # noqa: E402

CASES = PACK / "tests" / "cases.json"
GOLDEN = PACK / "tests" / "golden"
FLOAT_TOL = 1e-9


def load_cases():
    return json.loads(CASES.read_text())


def params_from_case(d):
    d = dict(d)
    if "buildings" in d:
        d["buildings"] = tuple(BuildingSpec(b["id"], b["tenure"], tuple(b["unit_areas"])) for b in d["buildings"])
    if "scene_rules" in d:
        d["scene_rules"] = SceneRules(**d["scene_rules"])
    return Params(**d)


def case_output(case):
    r = run_simulation(params_from_case(case["params"]))
    return {"frames": r.frames, "events": [e.__dict__ for e in r.events], "votes": [v.__dict__ for v in r.votes], "n_units": r.n_units, "n_buildings": r.n_buildings}


def scene_output(case):
    e = build_entities(case["rows"], SceneRules(), case["scene_seed"])
    return {"buildings": [{"id": b.id, "tenure": b.tenure, "unit_areas": list(b.unit_areas)} for b in e.buildings],
            "excluded": [list(x) for x in e.excluded]}


def diff(a, b, path="", tol=FLOAT_TOL):
    """First difference between two JSON-like values: exact for ints, strings, bools and None; tolerance for floats. None if equal."""
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        return None if (a == b and type(a) is type(b)) else f"{path}: {a!r} != {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, int) and isinstance(b, int):
            return None if a == b else f"{path}: {a} != {b}"
        ok = abs(a - b) <= tol * max(1.0, abs(a), abs(b)) and not (math.isnan(a) != math.isnan(b))
        return None if ok else f"{path}: {a!r} != {b!r}"
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = diff(x, y, f"{path}[{i}]", tol)
            if d:
                return d
        return None
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f"{path}: keys {sorted(set(a) ^ set(b))} differ"
        for k in a:
            d = diff(a[k], b[k], f"{path}.{k}", tol)
            if d:
                return d
        return None
    return f"{path}: type {type(a).__name__} != {type(b).__name__}"
