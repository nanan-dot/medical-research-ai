"""跨资源共享的幂等载荷身份。"""

import hashlib
import json
from collections.abc import Mapping

from app.modules.document_reader.errors import IdempotencyKeyReusedError


def payload_digest(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_payload_matches(current_digest: str, incoming_digest: str) -> None:
    if current_digest != incoming_digest:
        raise IdempotencyKeyReusedError("幂等键已用于不同请求")

