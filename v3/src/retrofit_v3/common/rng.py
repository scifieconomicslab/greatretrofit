"""Portable PRNG (mulberry32) shared with ``v3/js/prng.js``.

Everything is 32-bit integer arithmetic, so the Python and JavaScript
implementations produce identical integer streams. Float helpers are defined
identically in both languages; gaussian/lognormal use ``log``/``cos``/``exp``,
which agree to ~1 ulp between engines (tests compare with a tolerance).

Reference vectors: ``v3/test_v3/vectors/prng.json`` (checked by both suites).
"""
from __future__ import annotations

import math
from typing import Sequence, TypeVar

T = TypeVar("T")
_M = 0xFFFFFFFF
_TWO32 = 4294967296.0


def _imul(a: int, b: int) -> int:
    return (a * b) & _M


def mix32(h: int) -> int:
    """murmur3 fmix32 finaliser."""
    h &= _M
    h ^= h >> 16
    h = _imul(h, 0x85EBCA6B)
    h ^= h >> 13
    h = _imul(h, 0xC2B2AE35)
    h ^= h >> 16
    return h


def hash_uniform(seed: int, i: int, j: int = 0) -> float:
    """Stateless uniform in [0, 1) keyed by (seed, i, j).

    Use for per-agent, per-period draws so that changing a policy parameter
    never shifts the random numbers other agents see (common random numbers).
    """
    h = mix32((seed & _M) ^ _imul(i & _M, 0x9E3779B1))
    h = mix32(h ^ _imul(j & _M, 0x85EBCA6B))
    return h / _TWO32


class Rng:
    """mulberry32 generator with fixed helper definitions."""

    __slots__ = ("state",)

    def __init__(self, seed: int = 0):
        self.state = seed & _M

    def next_u32(self) -> int:
        self.state = (self.state + 0x6D2B79F5) & _M
        t = self.state
        t = _imul(t ^ (t >> 15), t | 1)
        t ^= (t + _imul(t ^ (t >> 7), t | 61)) & _M
        return (t ^ (t >> 14)) & _M

    def random(self) -> float:
        """Uniform in [0, 1)."""
        return self.next_u32() / _TWO32

    def gaussian(self) -> float:
        """Standard normal via Box-Muller (two uniforms per call, no cache)."""
        u1 = 1.0 - self.random()  # (0, 1]
        u2 = self.random()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def lognormal(self, mu: float, sigma: float) -> float:
        return math.exp(mu + sigma * self.gaussian())

    def uniform(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.random()

    def randint(self, n: int) -> int:
        """Integer in [0, n)."""
        return int(self.random() * n)

    def choice(self, seq: Sequence[T]) -> T:
        return seq[self.randint(len(seq))]

    def weighted_index(self, weights: Sequence[float]) -> int:
        """Index drawn proportionally to non-negative weights."""
        total = 0.0
        for w in weights:
            total += w
        x = self.random() * total
        acc = 0.0
        for k, w in enumerate(weights):
            acc += w
            if x < acc:
                return k
        return len(weights) - 1


def make_rng(seed: int = 0) -> Rng:
    return Rng(seed)
