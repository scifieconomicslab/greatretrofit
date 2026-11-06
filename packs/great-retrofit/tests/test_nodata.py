"""No-data representation: Python frames use None only where the frame schema says; the JS test checks the NaN side (skipped if node is absent)."""
import shutil
import subprocess
from pathlib import Path

import pytest

from retrofit_v3 import Params, run_simulation

NULLABLE = {"rebate_per_euro", "can_front_cost", "cost_per_retrofit", "cost_per_retrofit_parts", "net_cash_by_quintile"}


def test_python_frames_use_none_only_for_declared_nullable_series():
    r = run_simulation(Params(seed=1, n_buildings=24, horizon_months=24))
    first = r.frames[0]["series"]
    assert all(first["rebate_per_euro"][k] is None for k in range(5))
    assert first["cost_per_retrofit"] is None and first["cost_per_retrofit_parts"] is None
    for fr in r.frames:
        for k, v in fr["series"].items():
            if k not in NULLABLE:
                assert v is not None and not (isinstance(v, list) and None in v), k
        for b in fr["buildings"]:
            assert None not in b.values()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_pack_frames_use_nan_only_where_v3_has_none():
    r = subprocess.run(["node", str(Path(__file__).with_name("test_nodata.js"))], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
