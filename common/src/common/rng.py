"""Random number generation utilities."""
import numpy as np


def make_rng(seed: int | None = None) -> np.random.Generator:
    """Create a NumPy random Generator with the given seed."""
    if seed is None:
        return np.random.default_rng()
    return np.random.default_rng(seed)