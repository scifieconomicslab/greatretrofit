#!/usr/bin/env python3
"""Regenerate golden trajectories from the Python reference model.

    python3 packs/great-retrofit/tools/regen_golden.py

Writes tests/golden/<case>.json (frames, events) for every case in tests/cases.json, and
tests/golden/scene_tables.json. Run it only when the Python model or the cases change on purpose;
review the diff. Both languages are then checked against these files.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import golden_lib as g  # noqa: E402


def dump(path, obj):
    path.write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False) + "\n")


def main():
    cases = g.load_cases()
    g.GOLDEN.mkdir(parents=True, exist_ok=True)
    for case in cases["cases"]:
        out = g.case_output(case)
        n_ev = len(out["events"])
        print(f"{case['name']:42s} frames={len(out['frames']):4d} adopted_units={n_ev:4d} units={out['n_units']}")
        if n_ev == 0:
            print("  warning: no adoption in this case; it exercises little", file=sys.stderr)
        dump(g.GOLDEN / f"{case['name']}.json", out)
    dump(g.GOLDEN / "scene_tables.json", {c["name"]: g.scene_output(c) for c in cases["scene_table_cases"]})


if __name__ == "__main__":
    main()
