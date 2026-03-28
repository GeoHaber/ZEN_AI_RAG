"""
Core/input_guard.py — Input validation for RAG queries.

Ported from main-app (George branch) E-12 input length guard.
Validates query length, detects basic prompt-injection patterns,
and ensures Unicode safety for Romanian/multilingual text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MAX_QUERY_LENGTH = 8000  # characters (matches main-app E-12)

# Patterns commonly used in prompt-injection attempts
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?above", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>", re.IGNORECASE),
]


# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    valid: bool
    reason: Optional[str] = None
    sanitised_text: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_query(
    text: str,
    max_length: int = MAX_QUERY_LENGTH,
    check_injection: bool = True,
) -> ValidationResult:
    """Validate a user query before it enters the RAG pipeline.

    Returns ValidationResult with .valid=True and .sanitised_text set on success,
    or .valid=False with .reason explaining the rejection.
    """
    if not isinstance(text, str):
        return ValidationResult(valid=False, reason="Query must be a string")

    if not text.strip():
        return ValidationResult(valid=False, reason="Query is empty")

    if len(text) > max_length:
        return ValidationResult(
            valid=False,
            reason=f"Query exceeds {max_length} characters ({len(text)} given)",
        )

    if check_injection:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return ValidationResult(
                    valid=False,
                    reason="Query matches a prompt-injection pattern",
                )

    # Basic sanitisation: collapse excessive whitespace, strip
    sanitised = re.sub(r"\s+", " ", text).strip()

    return ValidationResult(valid=True, sanitised_text=sanitised)
