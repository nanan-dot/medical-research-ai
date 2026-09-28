# Note Library Backend V1.2 Traceability

## Scope and safety

- Domain prefix: `/api/v1/note-library`.
- Persistence is isolated in `app/modules/note_library/`; legacy `DocumentReadingNote` is read only by the explicit backfill service.
- Validation used temporary SQLite databases and temporary `DATA_DIR` values. No command connected to or upgraded `data/app.db`.
- Browser keyboard, focus, responsive layout, scroll restoration, and stale-response rendering remain frontend E2E gates. This backend work supplies the state, version, fingerprint, timestamp, and capability contracts only.

## Acceptance mapping

| AC | Behavioral test | Implementation | Result |
|---|---|---|---|
| NB-01 | `test_nb01_independent_note_and_draft_persist_across_sessions` | `model.py`, `service.py:create/get_draft` | PASS |
| NB-02 | `test_nb02_keyword_tag_research_intersection_and_self_excluding_facets` | `service.py:list_notes/facets` | PASS |
| NB-03 | `test_nb03_500_equal_timestamp_notes_have_stable_bounded_pages`; `test_1000_note_page_uses_bounded_query_count` | deterministic `(content_updated_at, id)` ordering, bounded page sizes, and bounded query count at 1,000 notes | PASS |
| NB-04 | `test_nb04_metadata_archive_roundtrip_does_not_create_revision` | metadata CAS, archive/unarchive | PASS |
| NB-05 | `test_nb05_two_real_sessions_allow_one_cas_winner_and_preserve_draft` | database conditional update in `repository.py:cas_note_revision` | PASS |
| NB-06 | `test_nb06_idempotent_save_replays_and_rejects_changed_request` | scoped `NoteSaveOperation` uniqueness and request hash | PASS |
| NB-07 | `test_nb07_autosave_and_formal_revision_are_separate` | `NoteDraft` CAS and immutable `NoteRevision` | PASS |
| NB-08 | `test_nb08_restore_adds_revision_and_preserves_old_identity` | additive restore revision | PASS |
| NB-09 | `test_nb09_zero_and_multiple_typed_sources_and_forged_quote_rejection` | revision-owned source links and server anchor quote comparison | PASS |
| NB-10 | `test_nb10_source_version_change_marks_review_without_rewriting_history` | fixed source version plus live status projection | PASS |
| NB-11 | `test_nb11_revocation_filters_detail_search_export_and_ai_input` | centralized source authorization projection | PASS |
| NB-12 | `test_nb12_multiple_context_links_unlink_without_permission_expansion` | note/research links separate from source permission | PASS |
| NB-13 | `test_nb13_core_crud_and_search_do_not_touch_model_provider` | injected optional AI boundary | PASS |
| NB-14 | `test_nb14_stale_ai_suggestion_cannot_overwrite_new_draft`, `test_nb14_ai_fake_boundary_tracks_lifecycle_timeout_and_cancel` | fixed input versions, queued/running/succeeded/failed/cancelled fake-execution states, timeout and adoption CAS | PASS |
| NB-15 | `test_nb15_cloud_consent_rejects_before_provider_call` | consent guard before provider invocation | PASS |
| NB-16 | `test_nb16_derivation_is_idempotent_and_pins_revision` | revision-pinned derivation uniqueness and unavailable target error | PASS |
| NB-17 | `test_nb17_malicious_markdown_url_is_safe_in_preview_and_export` | pure Markdown/link/filename sanitizers, no URL fetch | PASS |
| NB-18 | `test_nb18_dry_run_and_repeated_backfill_are_lossless_and_idempotent` | legacy tracking table and explicit dry-run/apply service | PASS |
| NB-19 | `test_nb19_backend_contract_exposes_workflow_state_and_capabilities`, `test_nb19_http_contract_and_nb20_conflict_envelope`, `test_homepage_views_counts_and_list_summaries`, `test_history_is_bounded_and_paginated` | draft state, homepage views/counts/summaries, history pagination, capabilities, query fingerprint/as-of and HTTP routes | PASS (backend); frontend E2E pending |
| NB-20 | `test_nb20_stale_autosave_is_rejected_without_losing_latest_draft`, `test_nb19_http_contract_and_nb20_conflict_envelope` | draft version CAS and request-aware conflict envelope | PASS (backend); frontend stale-response E2E pending |

## API contract

- `GET /notes?view=all|recent|favorite|unlinked_research|archived`, `GET /facets`, `POST /notes`, `GET /notes/{note_id}`. `recent` is the fixed rolling 30-day content-update view; list items include authorization-filtered source and ResearchContext summaries.
- `GET|PUT /notes/{note_id}/draft`
- `POST /notes/{note_id}/revisions`, `GET /notes/{note_id}/revisions?page=&page_size=`, `GET /notes/{note_id}/revisions/{revision_no}`
- `POST /notes/{note_id}/restore`, `PATCH /notes/{note_id}/metadata`
- `POST /notes/{note_id}/archive`, `POST /notes/{note_id}/unarchive`
- `POST /notes/{note_id}/ai-suggestions`
- `GET /ai-suggestions/{suggestion_id}`, `POST /ai-suggestions/{suggestion_id}/cancel|adopt`. Completion is intentionally not a public route; it remains an internal provider-service operation.
- `POST /notes/{note_id}/derivations`, `POST /exports`
- `POST /legacy-backfill?actor_scope=...&dry_run=true|false`

Errors use the repository envelope with stable `code`, safe `message`, and `request_id`. Validation failures from the domain may additionally contain field names, never note body content.

## Migration

- Revision: `n1b2c3d4e5f6`
- Parents: merge of concurrent heads `a2c4e6f8b0d1` and `b7d9f1a3c5e7`
- Creates only note-library tables, indexes, foreign keys, and uniqueness constraints; downgrade drops only those structures.

## Known structural limits

- Local `actor_scope` provides durable operator scoping, not production account authentication or tenant authorization. Remote-account release still requires an authenticated server identity and account-level authorization policy.
- The injected AI provider boundary and task states are testable, but this change does not add a production cloud worker. `NoteRead.capabilities` explicitly includes `ai_suggestions_unavailable` and `local_actor_scope_only`; clients must not present a production AI action or mistake local scope for account authorization.
- Claim and Evidence derivations return `TARGET_CAPABILITY_UNAVAILABLE`; writing creates only a revision-pinned candidate record.
- Frontend keyboard, focus, responsive behavior, saved scroll/filter restoration, and out-of-order network rendering require later browser E2E and are not claimed here.
