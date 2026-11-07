"""Parameter validation utilities.

The same rules, with the same accepted and rejected values, are in packs/great-retrofit/runtime.js (the v* helpers, Params); the shared vectors in
tests/model/validation_vectors.json are checked by both. A number is a real, finite number: not NaN, not +/-inf, not a bool, not a string, not None.
"""
import math
from dataclasses import fields
from typing import Any


def validate_finite(value: Any, name: str) -> None:
    """Validate that a value is a finite real number (int or float; bool, str, None, NaN and +/-inf are not)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{name} must be a finite number, got {value!r}")


def validate_positive(value: float, name: str) -> None:
    """Validate that a value is a finite positive number."""
    validate_finite(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_nonnegative(value: float, name: str) -> None:
    """Validate that a value is a finite non-negative number."""
    validate_finite(value, name)
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def validate_probability(value: float, name: str) -> None:
    """Validate that a value is a valid probability [0, 1]."""
    validate_finite(value, name)
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def validate_integer(value: Any, name: str) -> None:
    """Validate a whole number: an int, or a float with an integer value (JS has one number type, so 3.0 is 3 in both languages)."""
    validate_finite(value, name)
    if value != int(value):
        raise ValueError(f"{name} must be a whole number, got {value}")


def validate_integer_positive(value: int, name: str) -> None:
    """Validate that a value is a positive whole number."""
    validate_integer(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value}")


def validate_bool(value: Any, name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false, got {value!r}")


def validate_dataclass_positive(obj: Any, field_names: list[str]) -> None:
    """Validate that specified fields of a dataclass are positive."""
    for field_name in field_names:
        value = getattr(obj, field_name)
        validate_positive(value, field_name)


def validate_dataclass_nonnegative(obj: Any, field_names: list[str]) -> None:
    """Validate that specified fields of a dataclass are non-negative."""
    for field_name in field_names:
        value = getattr(obj, field_name)
        validate_nonnegative(value, field_name)
