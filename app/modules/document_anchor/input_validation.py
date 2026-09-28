"""验证受控路径解析之后的 PDF 字节身份，不记录原文路径。"""

import hashlib
from pathlib import Path

from app.common.exceptions import ConflictError, UnprocessableEntityError
from app.core.config import settings


def verify_pdf(path: Path, expected_hash: str) -> None:
    """Check signature, size and streaming SHA256; raises safe domain errors."""
    if not path.is_absolute() or path.suffix.lower() != ".pdf" or not path.is_file():
        raise UnprocessableEntityError("A controlled PDF file is required")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            prefix = source.read(1024)
            if not prefix.startswith(b"%PDF-"):
                raise UnprocessableEntityError("Invalid PDF signature")
            digest.update(prefix)
            size = len(prefix)
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > settings.PDF_TEXTITEM_EXTRACTOR_MAX_FILE_BYTES:
                    raise UnprocessableEntityError("PDF extraction file limit exceeded")
                digest.update(chunk)
            if size > settings.PDF_TEXTITEM_EXTRACTOR_MAX_FILE_BYTES:
                raise UnprocessableEntityError("PDF extraction file limit exceeded")
    except OSError as exc:
        raise UnprocessableEntityError("PDF file cannot be read") from exc
    if digest.hexdigest() != expected_hash:
        raise ConflictError(
            "PDF file version changed; synchronize the document before retrying"
        )
