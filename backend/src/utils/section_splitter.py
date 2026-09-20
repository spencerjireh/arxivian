"""Section splitting and code-side candidate finders over ingested paper text.

The Stage 2 scoring graph sends Jev (a select-not-generate model) targeted sections and
candidate spans as request state. This module turns `Paper.raw_text` (pypdf output from
the ingest path, newline-preserving) into those inputs. Ported from the
`jevexperiments` spike; normalization runs at read time so ingest text and chunks are
left untouched.

Every candidate list is tuned to over-find, deduplicated, kept in document order, and
capped: Jev cannot choose an omitted value.
"""

from __future__ import annotations

import re

# Canonical section keys and the heading words that map to them.
_HEADING_MAP: list[tuple[str, str]] = [
    (r"abstract", "abstract"),
    (r"introduction", "intro"),
    (r"related work|background|preliminaries", "related"),
    (
        r"methods?|approach|model(?: architecture)?|proposed method|architecture|framework",
        "method",
    ),
    (
        r"experiments?|experimental (?:setup|settings?|results|details)|setup"
        r"|training(?: details| setup| procedure)?|implementation(?: details)?|optimization",
        "experiments",
    ),
    (r"results?|evaluation|analysis", "results"),
    (r"discussion|limitations?|broader impacts?|ethical considerations?", "discussion"),
    (r"conclusions?(?: and future work)?|summary", "conclusion"),
    (r"acknowledg\w*", "ack"),
    (r"references|bibliography", "references"),
    (r"appendix|appendices|supplementary material", "appendix"),
]

# A whole line that is an optional numeric/letter/roman prefix plus a heading word.
_HEADING_RE = re.compile(
    r"^(?:(?:\d+|[A-Z]|[IVX]+)(?:\.\d+)*\.?\s+)?"
    r"(" + "|".join(pattern for pattern, _ in _HEADING_MAP) + r")\s*:?\s*$",
    re.IGNORECASE,
)

# Allows one line break or space right after the host, which PDF line wrapping inserts.
_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:github\.com|gitlab\.com|huggingface\.co|bitbucket\.org)/\s?[\w\-./]+",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\d])")
_CODE_MENTION_RE = re.compile(
    r"\bcode\b.*\b(?:available|release[sd]?|open[- ]source[d]?|public(?:ly)?)\b"
    r"|\b(?:available|release[sd]?)\b.*\bcode\b",
    re.IGNORECASE,
)
_REFERENCES_RE = re.compile(r"^\s*(?:\d+\.?\s+)?references\s*$", re.IGNORECASE | re.MULTILINE)

_LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"})

# Per-section character caps keep each Jev request well under the model's state limit
# (32k tokens for Jev 1.13, about 4 characters per token) even for 75-page papers.
SECTION_CHAR_CAP = 12_000

# Positional fallbacks (fractions of the body before references) used when a heading
# is not found. BERT-style papers title the method section after the model name.
_METHOD_FALLBACK = (0.15, 0.45)
_EXPERIMENTS_FALLBACK = (0.45, 0.75)


def normalize_text(text: str) -> str:
    """Expand LaTeX ligature glyphs and rejoin words hyphenated across a line break."""
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text.translate(_LIGATURES))


def split_sections(text: str) -> dict[str, str]:
    """Split by heading lines into canonical sections. Later duplicates append.

    Text before the first recognized heading lands under `"front"`; unrecognized
    headings never occur (the regex only matches mapped words).
    """
    sections: dict[str, list[str]] = {}
    current = "front"
    buffer: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = _HEADING_RE.match(stripped) if 0 < len(stripped) <= 60 else None
        if match:
            sections.setdefault(current, []).append("\n".join(buffer))
            buffer = []
            current = _canonical(match.group(1))
            continue
        buffer.append(line)
    sections.setdefault(current, []).append("\n".join(buffer))
    return {key: "\n".join(parts).strip() for key, parts in sections.items()}


def _canonical(heading: str) -> str:
    for pattern, key in _HEADING_MAP:
        if re.fullmatch(pattern, heading, re.IGNORECASE):
            return key
    return "other"


def body_before_references(text: str) -> str:
    """Cut the text at the first references heading."""
    match = _REFERENCES_RE.search(text)
    return text[: match.start()] if match else text


def positional_slice(text: str, start: float, end: float) -> str:
    """Slice by fraction of total length; the fallback when a heading is missing."""
    return text[int(len(text) * start) : int(len(text) * end)]


def sentences(text: str) -> list[str]:
    """Whitespace-flattened sentence split."""
    flat = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(flat) if s.strip()]


def _dedupe(items: list[str], cap: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
        if len(out) >= cap:
            break
    return out


def code_mentions(text: str, cap: int = 8) -> list[str]:
    """Repository URLs (line-wrap tolerant) plus sentences about code availability."""
    urls = [re.sub(r"\s+", "", u).rstrip(".") for u in _URL_RE.findall(text)]
    lines = [
        s
        for s in sentences(body_before_references(text))
        if _CODE_MENTION_RE.search(s) and len(s) <= 300
    ]
    return _dedupe(urls + lines, cap=cap)


def appendix_headings(appendix: str, cap: int = 20) -> list[str]:
    """Letter-numbered appendix heading lines ("A.1 Training details")."""
    lines = [line.strip() for line in appendix.splitlines()]
    heads = [
        line for line in lines if re.match(r"^[A-Z](?:\.\d+)*\.?\s+\S", line) and len(line) <= 80
    ]
    return _dedupe(heads, cap=cap)


def extract_sections(raw_text: str, abstract: str = "") -> dict[str, str]:
    """Build the section payloads the scoring nodes send as Jev state.

    Returns `{"abstract", "method", "experiments", "appendix_headings"}`. `method` and
    `experiments` fall back to positional slices of the body when no heading matched,
    and are capped at `SECTION_CHAR_CAP` characters. Empty `raw_text` yields empty strings.
    """
    if not raw_text:
        return {
            "abstract": abstract or "",
            "method": "",
            "experiments": "",
            "appendix_headings": "",
        }

    text = normalize_text(raw_text)
    sections = split_sections(text)
    body = body_before_references(text)

    method = sections.get("method") or positional_slice(body, *_METHOD_FALLBACK)
    experiments = "\n".join(
        part for part in (sections.get("experiments", ""), sections.get("results", "")) if part
    ) or positional_slice(body, *_EXPERIMENTS_FALLBACK)
    appendix = "\n".join(appendix_headings(sections.get("appendix", "")))

    return {
        "abstract": abstract or sections.get("abstract", "")[:SECTION_CHAR_CAP],
        "method": method[:SECTION_CHAR_CAP],
        "experiments": experiments[:SECTION_CHAR_CAP],
        "appendix_headings": appendix,
    }
