"""Shared utilities for agent tools."""

from datetime import datetime
from typing import Any


def parse_date(value: str | None, field: str) -> datetime | None:
    """Parse ISO date string, raising ValueError with descriptive message.

    Args:
        value: Date string in YYYY-MM-DD format, or None
        field: Field name for error messages (e.g., "start_date")

    Returns:
        Parsed datetime or None if value is None/empty

    Raises:
        ValueError: If the date string is malformed
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Invalid {field}: '{value}'. Expected format: YYYY-MM-DD")


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
