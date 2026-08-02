"""Bounded Markdown rendering helpers."""

import re

MAX_EVIDENCE_EXPORT = 4000


def escape_markdown(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", value)


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip(" .")
    cleaned = re.sub(r"\.{2,}", "-", cleaned)
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError("Export filename is invalid")
    return cleaned[:100]
