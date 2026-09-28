"""Deterministic cache identity; every safety-affecting version is fenced."""

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class CacheIdentity:
    access_scope: str
    document_id: int
    file_hash: str
    anchor_revision_id: int
    segmentation_revision_id: int
    source_anchor_id: int
    source_text_hash: str
    source_language: str
    target_language: str
    context_hash: str
    terminology_version: str
    provider: str
    model: str
    model_revision: str
    prompt_version: str
    config_version: str
    policy_version: str
    validator_version: str


def cache_key(identity: CacheIdentity) -> str:
    encoded = json.dumps(
        asdict(identity), sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
