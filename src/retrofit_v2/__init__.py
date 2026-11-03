"""v2 Retrofit Co-op Simulation Package.

This package implements the extended agent-based model with:
- Heterogeneous households (income, wealth, aspiration, tastes)
- Heterogeneous buildings (size, age, location)
- Limited search and matching
- Spatial neighbourhood structure
- Monitoring (Gini, price dispersion, time-on-market)
"""
from .params import Params
from .model import run_simulation
from .results import Result

__all__ = ["Params", "run_simulation", "Result"]