"""Shared utilities for agent tools."""

from typing import Any


def safe_list_from_jsonb(value: Any) -> list:
    """Safely convert a JSONB value to a list.

    Args:
        value: JSONB value that should be a list, or None

    Returns:
        The value as a list, or empty list if None/invalid
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    # If it's some other iterable, try to convert
    try:
        return list(value)
    except (TypeError, ValueError):
        return []
