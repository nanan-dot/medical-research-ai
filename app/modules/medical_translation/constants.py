"""Frozen Phase 1 versions and resource limits."""

TASK_TYPE = "medical_selection_translation"
PROMPT_VERSION = "medical-selection-prompt-v2"
CONFIG_VERSION = "medical-selection-config-v2"
POLICY_VERSION = "medical-safety-policy-v2"
VALIDATOR_VERSION = "medical-deterministic-validator-v2"
TERMINOLOGY_VERSION = "medct-local-terms-v3"
MAX_SOURCE_CHARACTERS = 8000
MAX_TRANSLATION_CHARACTERS = 16000
MAX_ATTEMPTS = 3
LEASE_SECONDS = 90
PHASE2_MAX_SEGMENTS_PER_INTENT = 12
PHASE2_PREFETCH_QUEUE_LIMIT = 24
PREFETCH_FAILURE_COOLDOWN_SECONDS = 60
