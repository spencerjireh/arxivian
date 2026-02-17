"""Shared utilities for agent tools."""

import re
from datetime import datetime
from typing import Any

_SHORT_DATE_RE = re.compile(r"^\d{2}-\d{2}$")


def parse_date(value: str | None, field: str) -> datetime | None:
    """Parse ISO date string, raising ValueError with descriptive message.

    Accepts YYYY-MM-DD or MM-DD (defaults to current year).

    Args:
        value: Date string in YYYY-MM-DD or MM-DD format, or None
        field: Field name for error messages (e.g., "start_date")

    Returns:
        Parsed datetime or None if value is None/empty

    Raises:
        ValueError: If the date string is malformed
    """
    if not value:
        return None

    # Strict MM-DD -> prepend current year
    if _SHORT_DATE_RE.match(value):
        value = f"{datetime.now().year}-{value}"

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Invalid {field}: '{value}'. Expected format: YYYY-MM-DD")


def format_paper_for_prompt(paper: dict, index: int) -> str:
    """Format a single paper dict into compact prompt text.

    Works with both arxiv_search and list_papers result shapes.

    Args:
        paper: Dict with arxiv_id, title, authors, abstract, categories, published_date
        index: 1-based display index
    """
    authors = paper.get("authors", [])
    if len(authors) > 3:
        author_str = f"{authors[0]}, {authors[1]}, {authors[2]} et al."
    elif authors:
        author_str = ", ".join(str(a) for a in authors)
    else:
        author_str = "Unknown"

    date_raw = paper.get("published_date", "")
    date_str = ""
    if date_raw:
        try:
            dt = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            date_str = str(date_raw)

    categories = ", ".join(paper.get("categories", []))

    abstract = paper.get("abstract", "")
    if len(abstract) > 150:
        abstract = abstract[:150].rsplit(" ", 1)[0] + "..."

    lines = [f'{index}. "{paper.get("title", "Untitled")}" by {author_str}']
    meta_parts = []
    if paper.get("arxiv_id"):
        meta_parts.append(f"ID: {paper['arxiv_id']}")
    if date_str:
        meta_parts.append(date_str)
    if categories:
        meta_parts.append(categories)
    if meta_parts:
        lines.append(f"   {' | '.join(meta_parts)}")
    if abstract:
        lines.append(f"   {abstract}")
    return "\n".join(lines)


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
