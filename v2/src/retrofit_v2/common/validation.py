"""Parameter validation utilities."""
from dataclasses import fields
from typing import Any


def validate_positive(value: float, name: str) -> None:
    """Validate that a value is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_nonnegative(value: float, name: str) -> None:
    """Validate that a value is non-negative."""
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def validate_probability(value: float, name: str) -> None:
    """Validate that a value is a valid probability [0, 1]."""
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def validate_integer_positive(value: int, name: str) -> None:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value}")


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