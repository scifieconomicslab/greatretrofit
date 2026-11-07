"""Property fuzz of the Python reference model: frame, state and event invariants at every step (see fuzz_lib.py and docs/state-machines.md).

Bounded run time (FUZZ_BUDGET_S, default 20 s; FUZZ_N cases per kind, default 150; FUZZ_SEED offsets the case seeds). A failure names (kind, case seed):
rebuild the case with ``fuzz_lib.case_for(kind, seed)``. Known, documented defects are NOT hidden here: lag 0, NaN, zero-unit buildings have their own
xfail repros under docs/state-machines/repro/ and the generators stay inside the region where the model is meant to be valid.
"""
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fuzz_lib as F  # noqa: E402

N = int(os.environ.get("FUZZ_N", "150"))
BUDGET = float(os.environ.get("FUZZ_BUDGET_S", "20"))
BASE = int(os.environ.get("FUZZ_SEED", "0"))


@pytest.mark.parametrize("kind", ["manifest", "edge"])
def test_invariants_hold_on_random_cases(kind):
    t0, ran, failures = time.time(), 0, []
    for i in range(N):
        if time.time() - t0 > BUDGET:
            break
        seed = BASE + i
        case = F.case_for(kind, seed)
        try:
            bad, _ = F.run_checked(case)
        except Exception as e:      # noqa: BLE001 - any exception on a valid case is a finding
            bad = [f"raised {type(e).__name__}: {e}"]
        ran += 1
        if bad:
            failures.append(f"{kind} seed {seed}: {bad[:3]}")
    assert ran >= min(N, 20), f"time budget too small: only {ran} cases ran"
    assert not failures, "\n".join(failures[:8])


def test_same_case_twice_is_identical():
    for seed in range(5):
        c = F.case_for("manifest", seed)
        a, b = F.run_checked(c, False)[1], F.run_checked(c, False)[1]
        assert a.frames == b.frames and a.events == b.events and a.votes == b.votes


def test_keep_frames_false_gives_same_final_frame():
    from dataclasses import replace
    from retrofit_v3 import run_simulation
    for seed in range(5):
        p = F.to_params(F.case_for("manifest", seed)["params"])
        assert run_simulation(p).final_frame == run_simulation(replace(p, keep_frames=False)).final_frame
