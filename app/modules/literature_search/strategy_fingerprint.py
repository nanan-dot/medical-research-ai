"""Canonical strategy fingerprints owned by the backend domain layer."""

import hashlib
import json
from typing import Any


def strategy_fingerprint(snapshot: dict[str, Any]) -> str:
    """Hash a normalized strategy representation for concurrency and stale-response guards."""
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
