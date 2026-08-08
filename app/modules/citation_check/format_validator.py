"""引用标识符 L1 格式校验。"""

import re
from dataclasses import dataclass
from typing import Literal

CitationKind = Literal["pmid", "doi"]
_IDENTIFIER_PATTERNS = {
    "pmid": re.compile(r"^\d{1,8}$"),
    "doi": re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE),
}


@dataclass(frozen=True)
class FormatValidation:
    status: Literal["format_valid", "invalid_format"]
    normalized: str
    reason: str | None = None


def validate_identifier(kind: CitationKind, identifier: str) -> FormatValidation:
    normalized = identifier.strip().lower() if kind == "doi" else identifier.strip()
    pattern = _IDENTIFIER_PATTERNS[kind]
    if not pattern.fullmatch(normalized):
        return FormatValidation("invalid_format", normalized, f"Invalid {kind} format")
    return FormatValidation("format_valid", normalized)
