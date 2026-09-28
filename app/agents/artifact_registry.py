"""Versioned, exact Artifact type policies for identity and invalidation."""

from dataclasses import dataclass

from app.agents.enums import ArtifactValidityStatus
from app.agents.hash_schema import content_hash


@dataclass(frozen=True)
class ArtifactTypePolicy:
    artifact_key_field: str
    version_key_field: str
    hash_field: str
    downstream_status: ArtifactValidityStatus
    schema_version: str = "1"


STALE = ArtifactValidityStatus.STALE
REVALIDATE = ArtifactValidityStatus.NEEDS_REVALIDATION

# Changing this table is a public-contract change and requires a new registry version.
ARTIFACT_REGISTRY_VERSION = "m0-artifact-registry-v1"
ARTIFACT_TYPE_POLICIES: dict[str, ArtifactTypePolicy] = {
    "literature_selection": ArtifactTypePolicy(
        "selection_id", "version", "selection_hash", STALE
    ),
    "evidence_version": ArtifactTypePolicy(
        "evidence_id", "evidence_version_id", "content_hash", STALE
    ),
    "evidence_set_snapshot": ArtifactTypePolicy(
        "evidence_set_snapshot_id", "version", "set_hash", STALE
    ),
    "study_identity_snapshot": ArtifactTypePolicy(
        "snapshot_id", "version", "hash", STALE
    ),
    "analysis_input_snapshot": ArtifactTypePolicy(
        "analysis_input_snapshot_id", "version", "input_hash", STALE
    ),
    "evidence_matrix_snapshot": ArtifactTypePolicy(
        "matrix_id", "matrix_snapshot_id", "content_hash", STALE
    ),
    "comparison_snapshot": ArtifactTypePolicy(
        "comparison_id", "comparison_snapshot_id", "content_hash", STALE
    ),
    "synthesis_draft_revision": ArtifactTypePolicy(
        "draft_id", "draft_revision_id", "content_hash", REVALIDATE
    ),
    "synthesis_version": ArtifactTypePolicy(
        "synthesis_id", "synthesis_version_id", "content_hash", REVALIDATE
    ),
    "synthesis_handoff": ArtifactTypePolicy(
        "handoff_id", "handoff_version_id", "content_hash", REVALIDATE
    ),
    "design_input_snapshot": ArtifactTypePolicy(
        "snapshot_id", "version", "content_hash", REVALIDATE
    ),
    "variable_dictionary": ArtifactTypePolicy(
        "dictionary_id", "version", "content_hash", REVALIDATE
    ),
    "feasibility_assessment": ArtifactTypePolicy(
        "assessment_id", "version", "content_hash", REVALIDATE
    ),
    "study_design_draft_revision": ArtifactTypePolicy(
        "draft_id", "draft_revision_id", "content_hash", REVALIDATE
    ),
    "design_validation_report": ArtifactTypePolicy(
        "report_id", "version", "content_hash", REVALIDATE
    ),
    "study_design_version": ArtifactTypePolicy(
        "study_design_id", "study_design_version_id", "content_hash", REVALIDATE
    ),
    "writing_input_bundle": ArtifactTypePolicy(
        "bundle_id", "bundle_version", "bundle_hash", REVALIDATE
    ),
    "manuscript_draft_revision": ArtifactTypePolicy(
        "draft_id", "draft_revision_id", "content_hash", REVALIDATE
    ),
    "citation_binding_snapshot": ArtifactTypePolicy(
        "snapshot_id", "version", "content_hash", REVALIDATE
    ),
    "claim_support_report": ArtifactTypePolicy(
        "report_id", "version", "content_hash", REVALIDATE
    ),
    "citation_audit_report": ArtifactTypePolicy(
        "report_id", "version", "content_hash", REVALIDATE
    ),
    "writing_validation_report": ArtifactTypePolicy(
        "report_id", "version", "content_hash", REVALIDATE
    ),
    "rendered_page_manifest": ArtifactTypePolicy(
        "page_manifest_id", "version", "content_hash", REVALIDATE
    ),
    "render_review_decision": ArtifactTypePolicy(
        "decision_id", "version", "content_hash", REVALIDATE
    ),
    "render_validation_report": ArtifactTypePolicy(
        "report_id", "version", "content_hash", REVALIDATE
    ),
    "package_candidate_manifest": ArtifactTypePolicy(
        "manifest_id", "version", "content_hash", REVALIDATE
    ),
    "submission_package_version": ArtifactTypePolicy(
        "package_id", "package_version_id", "content_hash", REVALIDATE
    ),
    # M0-only fixtures remain exact registered types and cannot be used as domain handoffs.
    "source": ArtifactTypePolicy("document", "revision", "_computed", STALE),
    "analysis": ArtifactTypePolicy("result", "result", "_computed", STALE),
    "draft": ArtifactTypePolicy("claim", "claim", "_computed", REVALIDATE),
    "test": ArtifactTypePolicy("value", "value", "_computed", STALE),
}
ARTIFACT_REGISTRIES = {ARTIFACT_REGISTRY_VERSION: ARTIFACT_TYPE_POLICIES}


def policy_for(
    artifact_type: str, registry_version: str = ARTIFACT_REGISTRY_VERSION
) -> ArtifactTypePolicy:
    try:
        return ARTIFACT_REGISTRIES[registry_version][artifact_type]
    except KeyError as exc:
        raise ValueError(
            f"unknown artifact_type or registry version: "
            f"{registry_version}/{artifact_type}"
        ) from exc


def validate_typed_ref(
    *,
    artifact_type: str,
    artifact_key: str,
    version_key: str,
    schema_version: str,
    payload: dict[str, object],
    registry_version: str = ARTIFACT_REGISTRY_VERSION,
) -> str:
    policy = policy_for(artifact_type, registry_version)
    if schema_version != policy.schema_version:
        raise ValueError("artifact schema_version is not registered")
    if policy.hash_field == "_computed":
        return content_hash(payload)
    if str(payload.get(policy.artifact_key_field, "")) != artifact_key:
        raise ValueError("artifact_key does not match authoritative typed_ref")
    if str(payload.get(policy.version_key_field, "")) != version_key:
        raise ValueError("version_key does not match authoritative typed_ref")
    supplied_hash = payload.get(policy.hash_field)
    if not isinstance(supplied_hash, str) or len(supplied_hash) != 64:
        raise ValueError("typed_ref authoritative hash is missing")
    hash_payload = {
        key: value for key, value in payload.items() if key != policy.hash_field
    }
    calculated = content_hash(hash_payload)
    if supplied_hash != calculated:
        raise ValueError("typed_ref authoritative hash does not match payload")
    return calculated
