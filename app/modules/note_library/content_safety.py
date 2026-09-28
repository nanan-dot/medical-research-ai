"""Pure content-safety helpers for preview and export contracts."""

import re
from urllib.parse import urlparse

_DANGEROUS_BLOCKS = re.compile(
    r"<\s*(script|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAGS = re.compile(r"<[^>]+>")
_MARKDOWN_LINK = re.compile(r"(!?)\[([^]]*)\]\(([^)]+)\)")
_SAFE_PROTOCOLS = {"http", "https", "mailto"}


def safe_markdown(value: str) -> str:
    """Remove executable HTML and unsafe link targets without network access."""
    value = _DANGEROUS_BLOCKS.sub("", value)
    value = _HTML_TAGS.sub("", value)

    def replace(match: re.Match[str]) -> str:
        is_image, label, target = match.groups()
        if is_image:
            return label
        protocol = urlparse(target.strip()).scheme.casefold()
        return match.group(0) if protocol in _SAFE_PROTOCOLS else label

    return _MARKDOWN_LINK.sub(replace, value)


def safe_filename(title: str, suffix: str) -> str:
    """Create a portable leaf filename; no caller-controlled directories."""
    stem = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", title).strip(" ._")
    return f"{(stem or 'note')[:120]}.{suffix}"


def safe_url(value: str | None) -> str | None:
    if not value:
        return None
    return value if urlparse(value).scheme.casefold() in _SAFE_PROTOCOLS else None
