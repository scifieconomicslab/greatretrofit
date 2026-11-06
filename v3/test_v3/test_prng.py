"""PRNG tests: shared vectors (also checked by v3/js/test_prng.js)."""
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from retrofit_v3.common.rng import Rng, hash_uniform

V3 = Path(__file__).resolve().parents[1]
VECTORS = json.loads((V3 / "test_v3" / "vectors" / "prng.json").read_text())


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: f"seed{c['seed']}")
def test_vectors(case):
    s = case["seed"]
    g = lambda: Rng(s)  # noqa: E731
    r = g(); assert [r.next_u32() for _ in range(8)] == case["u32"]
    r = g(); assert [r.random() for _ in range(8)] == case["random"]
    r = g(); assert [r.gaussian() for _ in range(6)] == pytest.approx(case["gaussian"], abs=1e-12)
    mu, sg = VECTORS["lognormal"]
    r = g(); assert [r.lognormal(mu, sg) for _ in range(6)] == pytest.approx(case["lognormal"], abs=1e-12)
    r = g(); assert [r.randint(10) for _ in range(10)] == case["randint10"]
    r = g(); assert [r.randint(1000) for _ in range(10)] == case["randint1000"]
    r = g(); assert [r.choice(VECTORS["choices"]) for _ in range(10)] == case["choice"]
    r = g(); assert [r.weighted_index(VECTORS["weights"]) for _ in range(12)] == case["weighted_index"]
    r = g(); assert [r.uniform(-2.0, 3.0) for _ in range(5)] == pytest.approx(case["uniform"], abs=1e-15)
    for i, j, u in case["hash_uniform"]:
        assert hash_uniform(s, i, j) == u


def test_mulberry32_reference_value():
    # widely published first output of mulberry32 with seed 0
    assert Rng(0).random() == pytest.approx(0.2664292086847126, abs=1e-15)


def test_ranges_and_moments():
    r = Rng(7)
    xs = [r.random() for _ in range(20000)]
    assert all(0.0 <= x < 1.0 for x in xs)
    assert abs(sum(xs) / len(xs) - 0.5) < 0.01
    gs = [r.gaussian() for _ in range(20000)]
    m = sum(gs) / len(gs)
    sd = math.sqrt(sum((g - m) ** 2 for g in gs) / len(gs))
    assert abs(m) < 0.03 and abs(sd - 1) < 0.03
    assert all(0 <= r.randint(5) < 5 for _ in range(1000))


def test_hash_uniform_is_stateless_and_spread():
    assert hash_uniform(1, 2, 3) == hash_uniform(1, 2, 3)
    assert hash_uniform(1, 2, 3) != hash_uniform(1, 3, 2)
    xs = [hash_uniform(5, i, 0) for i in range(5000)]
    assert abs(sum(xs) / len(xs) - 0.5) < 0.02


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_matches_vectors():
    out = subprocess.run(["node", str(V3 / "js" / "test_prng.js")],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
