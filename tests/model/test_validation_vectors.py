"""Issue #4 (SM-2, SM-3, SM-10): one validation rule set, in both languages, checked on the same vectors.

validation_vectors.json lists inputs to Params() with 'accept': true/false. Python (this file) and node (validation_vectors.js) must give the
expected answer on every one, so the two languages accept and reject exactly the same inputs. An accepted vector must also run (2 steps) with finite output.
"""
import json
import math
import shutil
from pathlib import Path

import pytest

import fuzz_lib as F
from node_util import needs_node, run_node
from retrofit_v3 import Params
from retrofit_v3.entities import BuildingSpec
from retrofit_v3.model import Simulation
from retrofit_v3.scene_entities import SceneRules

DOC = json.loads((Path(__file__).parent / "validation_vectors.json").read_text())
VECTORS = DOC["vectors"]
SENTINEL = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}


def dec(v):
    if isinstance(v, list):
        return [dec(x) for x in v]
    if isinstance(v, dict):
        return SENTINEL[v["$"]] if "$" in v else {k: dec(x) for k, x in v.items()}
    return v


def build(params):
    kw = dec(params)
    if isinstance(kw.get("buildings"), list):
        kw["buildings"] = [BuildingSpec(b.get("id"), b.get("tenure"), b.get("unit_areas"), b.get("rental_draw")) if isinstance(b, dict) else b for b in kw["buildings"]]
    if isinstance(kw.get("scene_rules"), dict):
        kw["scene_rules"] = SceneRules(**kw["scene_rules"])
    return Params(**kw)


def py_accepts(v):
    try:
        return build(v["params"])
    except (ValueError, TypeError):
        return None


def test_vector_names_are_unique_and_both_outcomes_are_covered():
    names = [v["name"] for v in VECTORS]
    assert len(names) == len(set(names))
    assert sum(v["accept"] for v in VECTORS) >= 15 and sum(not v["accept"] for v in VECTORS) >= 300


@pytest.mark.parametrize("v", VECTORS, ids=lambda v: v["name"])
def test_python_gives_the_expected_answer(v):
    p = py_accepts(v)
    assert (p is not None) == v["accept"], f"{v['name']}: expected {'accept' if v['accept'] else 'reject'}"
    if p is not None:
        sim = Simulation(Params(**{**{f: getattr(p, f) for f in p.__dataclass_fields__}, "horizon_months": 2}))
        sim.step(); sim.step()
        bad = [path for path, x in F._walk_numbers(sim.frame) if not math.isfinite(x)]
        assert not bad, bad[:3]


@needs_node
def test_js_gives_the_expected_answer_on_every_vector():
    out = run_node("validation_vectors.js")
    assert [o["name"] for o in out] == [v["name"] for v in VECTORS]
    wrong = [f"{o['name']}: JS {'accepts' if o['accepted'] else 'rejects (' + o.get('error', '') + ')'}, expected {'accept' if v['accept'] else 'reject'}"
             for o, v in zip(out, VECTORS) if o["accepted"] != v["accept"]]
    assert not wrong, "\n".join(wrong[:15])


@needs_node
def test_python_and_js_reject_with_a_message_that_names_the_field():
    """Not only the same verdict: a rejected number vector says which field (a quick check on the first word of the message)."""
    out = {o["name"]: o for o in run_node("validation_vectors.js")}
    for v in VECTORS:
        if v["accept"] or " = " not in v["name"]:
            continue
        field = v["name"].split(" = ")[0]
        assert field in out[v["name"]]["error"], (v["name"], out[v["name"]])
        with pytest.raises((ValueError, TypeError)) as e:
            build(v["params"])
        assert field in str(e.value), (v["name"], str(e.value))


@needs_node
def test_js_params_does_not_coerce_types():
    """SM-10: null, numeric strings, [] and 1 for a boolean are rejected (they used to be accepted by JS comparisons)."""
    import subprocess
    r = subprocess.run(["node", str(Path(__file__).parent / "params_coercion.js")], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
