"""Security utilities for prompt injection detection."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InjectionScanResult:
    """Result of scanning text for injection patterns."""

    is_suspicious: bool
    matched_patterns: tuple[str, ...]


_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
        r"disregard\s+(everything|all|prior)",
        r"you\s+are\s+now\s+a",
        r"pretend\s+(to\s+be|you'?re)",
        r"act\s+as\s+(a|an|if)",
        r"new\s+(instructions?|rules?):",
        r"system\s*prompt",
        r"<\|.*?\|>",
        r"\[INST\]|\[/INST\]",
        r"score\s*(it|this)?\s*as\s*\d+",
        r"(set|mark|make)\s*(is_in_scope|in_scope)\s*[=:]",
        r"override\s+(\w+\s+)?(safety|guardrail|filter)",
    ]
)


def scan_for_injection(text: str) -> InjectionScanResult:
    """Scan text for prompt injection patterns."""
    matched = tuple(p.pattern for p in _INJECTION_PATTERNS if p.search(text))
    return InjectionScanResult(is_suspicious=bool(matched), matched_patterns=matched)
