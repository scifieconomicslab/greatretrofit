"""v3 retrofit model: monthly, economic (NPV + financing), three delivery modes."""
from .params import Params
from .model import run_simulation
from .results import Result

__all__ = ["Params", "run_simulation", "Result"]
