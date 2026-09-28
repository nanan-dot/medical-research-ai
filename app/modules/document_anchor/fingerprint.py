"""Deterministic identities for immutable A0 extraction revisions."""

import hashlib
import json
import math
import struct
from collections.abc import Mapping


def _canonical_value(value: object) -> object:
    # 数值用 IEEE754 大端位串，无损且不依赖 Python/JS 的十进制格式化。
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite canonical number")
        return {"$f64": struct.pack(">d", number if number else 0.0).hex()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _canonical_value(value[key])
            for key in sorted(value, key=lambda key: key.encode("utf-16-be"))
        }
    raise ValueError("Unsupported canonical value")


def canonical_json(value: object) -> str:
    """Serialize the versioned A0 binary64 canonical projection as UTF-8 JSON."""
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    """Return a UTF-8 SHA-256 digest."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_fingerprint(
    file_sha256: str,
    extractor_version: str,
    pdfjs_version: str,
    normalization_version: str,
    options_hash: str,
) -> str:
    """Identify a repeatable extraction request before trailer validation."""
    return sha256_text(
        f"{file_sha256}|{extractor_version}|{pdfjs_version}|"
        f"{normalization_version}|{options_hash}"
    )


def document_content_hash(page_hashes: list[str]) -> str:
    """Combine already ordered page hashes into the document content identity."""
    return sha256_text("|".join(page_hashes))


def extraction_fingerprint(request_hash: str, content_hash: str) -> str:
    """Identify a fully validated immutable revision."""
    return sha256_text(f"{request_hash}|{content_hash}")


def record_hash(record: Mapping[str, object]) -> str:
    """Hash a contract record after caller removes self-referential hash fields."""
    return sha256_text(canonical_json(record))
