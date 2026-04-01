"""Text processing utilities."""
from __future__ import annotations

import re
from typing import List, Optional


_HEDGING_PHRASES = [
    "i don't know",
    "i do not know",
    "i'm not sure",
    "i am not sure",
    "cannot determine",
    "not enough information",
    "insufficient information",
    "unable to answer",
    "no information available",
    "not mentioned in",
    "not provided",
    "unclear from",
    "cannot confirm",
    "may not be accurate",
    "please consult",
    "uncertain",
]

_NUMERIC_PATTERN = re.compile(
    r"""
    (?:
        \d{1,3}(?:,\d{3})*(?:\.\d+)?   # 1,234.56
        | \d+(?:\.\d+)?                 # 123.45
    )
    \s*(?:%|percent|mg|g|kg|ml|mcg|µg|IU|kcal|mmol|nmol)?
    """,
    re.VERBOSE | re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Remove excessive whitespace, null bytes, and normalize line endings."""
    if not text:
        return ""
    text = text.replace("\x00", "")
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_to_tokens(text: str, max_tokens: int, chars_per_token: int = 4) -> str:
    """Approximate token truncation by character count."""
    max_chars = max_tokens * chars_per_token
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Try to cut at last sentence boundary
    last_period = max(
        truncated.rfind(". "),
        truncated.rfind(".\n"),
    )
    if last_period > max_chars // 2:
        return truncated[: last_period + 1]
    return truncated


def extract_numbers(text: str) -> List[str]:
    """Return all numeric tokens found in text."""
    return _NUMERIC_PATTERN.findall(text)


def contains_hedging(text: str) -> bool:
    """Return True if text contains uncertainty/hedging phrases."""
    lower = text.lower()
    return any(phrase in lower for phrase in _HEDGING_PHRASES)


def count_words(text: str) -> int:
    """Return approximate word count."""
    if not text:
        return 0
    return len(text.split())


def split_sentences(text: str) -> List[str]:
    """Very simple sentence splitter on '. ', '? ', '! '."""
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    return [p for p in parts if p]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
