"""Browser-compatible UTF-16 offsets for immutable A2 selection ranges."""


class SelectionRangeError(ValueError):
    """Raised when a browser UTF-16 range splits a Unicode scalar value."""


def utf16_length(text: str) -> int:
    """Return the browser DOM-compatible UTF-16 code-unit length."""
    return len(text.encode("utf-16-le")) // 2


def slice_utf16(text: str, start_offset: int, end_offset: int) -> str:
    """Return a half-open UTF-16 range, rejecting a surrogate-pair midpoint."""
    if start_offset < 0 or end_offset < start_offset:
        raise SelectionRangeError("UTF-16 offsets must form a non-negative range")
    encoded = text.encode("utf-16-le")
    total = len(encoded) // 2
    if end_offset > total:
        raise SelectionRangeError("UTF-16 offset exceeds text length")
    start = start_offset * 2
    end = end_offset * 2
    try:
        encoded[:start].decode("utf-16-le")
        encoded[:end].decode("utf-16-le")
        return encoded[start:end].decode("utf-16-le")
    except UnicodeDecodeError as error:
        raise SelectionRangeError("UTF-16 offset splits a surrogate pair") from error
