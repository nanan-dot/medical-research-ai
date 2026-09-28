"""HashSchema V2 的唯一实现入口。"""

from __future__ import annotations

import hashlib
from typing import Any


class CanonicalizationError(ValueError):
    """输入无法形成冻结的规范载荷。"""


def canonical_json(value: Any) -> bytes:
    """使用 RFC 8785 JCS 序列化。

    生产环境没有可用实现时明确失败，避免用普通 JSON 排序冒充 JCS。
    """

    try:
        import rfc8785
    except ImportError as exc:  # pragma: no cover - exercised in deployment checks
        raise CanonicalizationError(
            "RFC 8785 implementation is required; install rfc8785"
        ) from exc
    try:
        result = rfc8785.dumps(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CanonicalizationError("value is not RFC 8785 canonicalizable") from exc
    if not isinstance(result, bytes):
        result = result.encode("utf-8")
    return result


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()
