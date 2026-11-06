"""Regenerate v3/test_v3/vectors/prng.json from the Python implementation.

Run only when the PRNG definition intentionally changes (it should not).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retrofit_v3.common.rng import Rng, hash_uniform  # noqa: E402

SEEDS = [0, 1, 42, 123456789, 4294967295]
CHOICES = ["a", "b", "c", "d", "e"]
WEIGHTS = [1.0, 2.0, 3.0, 4.0]


def build():
    out = {"choices": CHOICES, "weights": WEIGHTS, "lognormal": [0.5, 0.25], "cases": []}
    for s in SEEDS:
        g = Rng(s); u32 = [g.next_u32() for _ in range(8)]
        g = Rng(s); rnd = [g.random() for _ in range(8)]
        g = Rng(s); gau = [g.gaussian() for _ in range(6)]
        g = Rng(s); logn = [g.lognormal(0.5, 0.25) for _ in range(6)]
        g = Rng(s); ri10 = [g.randint(10) for _ in range(10)]
        g = Rng(s); ri1000 = [g.randint(1000) for _ in range(10)]
        g = Rng(s); ch = [g.choice(CHOICES) for _ in range(10)]
        g = Rng(s); wi = [g.weighted_index(WEIGHTS) for _ in range(12)]
        g = Rng(s); uni = [g.uniform(-2.0, 3.0) for _ in range(5)]
        hu = [[i, j, hash_uniform(s, i, j)] for i in (0, 1, 7, 4294967295) for j in (0, 3)]
        out["cases"].append({"seed": s, "u32": u32, "random": rnd, "gaussian": gau,
                             "lognormal": logn, "randint10": ri10, "randint1000": ri1000,
                             "choice": ch, "weighted_index": wi, "uniform": uni,
                             "hash_uniform": hu})
    return out


if __name__ == "__main__":
    path = ROOT / "test_v3" / "vectors" / "prng.json"
    path.write_text(json.dumps(build(), indent=1) + "\n")
    print("wrote", path)
