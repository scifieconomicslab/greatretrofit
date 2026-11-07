"""Python-vs-JavaScript comparison helpers for the fuzz harness (frame by frame, beyond the golden cases)."""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

import fuzz_lib as F
from retrofit_v3.model import run_simulation

HERE = Path(__file__).resolve().parent
REL = 1e-9


def diff(a, b, path="", rel=REL):
    """First difference between two JSON trees (floats within rel/abs tolerance), or None."""
    if isinstance(a, str) and a in ("NaN", "Infinity", "-Infinity"):
        return None if a == b else f"{path}: {a!r} vs {b!r}"
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        return None if a == b else f"{path}: {a!r} vs {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return None
        if isinstance(b, str) or not (math.isfinite(a) and math.isfinite(b)):
            return f"{path}: {a!r} vs {b!r}"
        return None if abs(a - b) <= rel * max(1.0, abs(a), abs(b)) else f"{path}: {a!r} vs {b!r}"
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f"{path}: keys {sorted(set(a) ^ set(b))}"
        for k in a:
            d = diff(a[k], b[k], f"{path}.{k}", rel)
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = diff(x, y, f"{path}[{i}]", rel)
            if d:
                return d
        return None
    return f"{path}: types {type(a).__name__} vs {type(b).__name__}"


def python_side(case):
    p = F.to_params(case["params"])
    r = run_simulation(p)
    return json.loads(json.dumps({"frames": r.frames, "events": [asdict(e) for e in r.events], "votes": [asdict(v) for v in r.votes]}))


def expected_pack_frame(fr):
    """What the adapter (runtime.js toPackFrame) must hold for a v3 frame, written independently from the Python frame."""
    states = ["not_retrofitted", "partial", "retrofitted", "not_modelled"]
    tenures = ["owner_occupied", "condo", "rental"]
    shareds = ["none", "pending", "approved"]
    B = fr["buildings"]
    done = [round(b["adopted_share"] * b["units"]) for b in B]
    s = fr["series"]
    nan = lambda x: "NaN" if x is None else x   # noqa: E731
    return {
        "t": fr["t"],
        "building": {
            "state": [states.index(b["state"]) for b in B], "tenure": [tenures.index(b["tenure"]) for b in B],
            "adopted_share": [b["adopted_share"] for b in B], "units": [b["units"] for b in B], "units_done": done,
            "cannot_front": [1 if (b["units_cannot_front"] > 0 and b["units_cannot_front"] == b["units"] - d) else 0 for b, d in zip(B, done)],
            "income_q_mean": [b["income_q_mean"] for b in B], "shared_state": [shareds.index(b["shared_state"]) for b in B]},
        "series": {
            "adoption_by_quintile": s["adoption_by_quintile"], "rebate_per_euro": [nan(x) for x in s["rebate_per_euro"]],
            "can_front_cost": [nan(x) for x in s["can_front_cost"]], "cost_per_retrofit": [nan(s["cost_per_retrofit"])],
            "public_cost": [s["public_cost"]], "bills_saved": [s["bills_saved"]],
            "buildings_by_state": [s["state_counts"][k] for k in states],
            "cost_parts": ["NaN", "NaN"] if s["cost_per_retrofit_parts"] is None else [s["cost_per_retrofit_parts"]["base"], s["cost_per_retrofit_parts"]["markup"]],
            "canvass_hours": s["canvass_hours_by_quintile"], "leisure_hours": s["leisure_hours_by_quintile"],
            "net_cash_by_quintile": [nan(x) for x in s["net_cash_by_quintile"]],
            "shared_by_state": [s["shared_counts"]["pending"], s["shared_counts"]["approved"]],
            "buildings_by_tenure": [s["tenure_counts"][k] for k in tenures],
            "rental_share": [s["tenure_counts"]["rental"] / len(B) if B else 0.0]},
    }


def got_pack_frame(af):
    return {"t": af["t"], "building": af["entities"]["building"], "series": af["series"]}


def run_js(cases, timeout=600):
    d = tempfile.mkdtemp(prefix="fuzz-js-")
    try:
        cp, op = os.path.join(d, "cases.json"), os.path.join(d, "out.json")
        Path(cp).write_text(json.dumps(cases))
        r = subprocess.run(["node", str(HERE / "run_js_cases.js"), cp, op], capture_output=True, text=True, timeout=timeout)
        if r.returncode:
            raise RuntimeError(r.stderr[-2000:])
        return json.loads(Path(op).read_text())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def compare(case, js):
    """Problems for one case: core frames/events/votes vs Python, adapter frames vs Python-derived expectation."""
    bad = []
    if "core_error" in js:
        return [f"JS core threw: {js['core_error']}"]
    py = python_side(case)
    d = diff(py, js["core"])
    if d:
        bad.append(f"core differs from Python at {d}")
    if "adapter_error" in js:
        bad.append(f"JS adapter threw: {js['adapter_error']}")
    else:
        for fr, af in zip(py["frames"], js["adapter"]):
            d = diff(expected_pack_frame(fr), got_pack_frame(af))
            if d:
                bad.append(f"adapter frame t={fr['t']} differs from Python-derived expectation at {d}")
                break
        if len(js["adapter"]) != len(py["frames"]):
            bad.append("adapter frame count")
    return bad
