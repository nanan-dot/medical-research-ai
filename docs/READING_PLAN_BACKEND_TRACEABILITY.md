# Core reading plan backend: design and acceptance traceability

## Design boundary

The feature is split into `model`, `schema`, `repository`, `service`, and
`selection`. Selection is a deterministic pure function. The repository owns
SQLAlchemy queries, the service owns transactions and domain rules, and the
router owns HTTP validation/serialization. Plans are immutable versions;
generation persists every item before the new plan becomes active. Existing
`reading-order` endpoints remain unchanged.

The evidence contract is intentionally metadata-only: PubMed position,
bibliographic fields, abstract availability/content, MeSH, PublicationType,
persisted OpenAlex signals, and configured journal metrics may be used. Missing
signals are recorded as `unavailable`/`not_collected`, never coerced to zero.
Restricted full text that was not obtained is never represented as analysed.

## AC to test traceability

### Reading plan V2 maturity acceptance

| AC | Behavioral test |
|---|---|
| AC-RPB-01 | `test_ac_rpb_01_02_03_reason_is_chinese_honest_and_persisted` |
| AC-RPB-02 | `test_ac_rpb_01_02_03_reason_is_chinese_honest_and_persisted` |
| AC-RPB-03 | `test_ac_rpb_01_02_03_reason_is_chinese_honest_and_persisted` |
| AC-RPB-04 | `test_ac_rpb_04_volume_issue_pages_and_null_mapping` |
| AC-RPB-05 | `test_ac_rpb_05_06_08_versions_failure_and_preserve` |
| AC-RPB-06 | `test_ac_rpb_05_06_08_versions_failure_and_preserve` |
| AC-RPB-07 | database partial unique index `uq_reading_plan_one_active`; conflict boundary in `generate` |
| AC-RPB-08 | `test_ac_rpb_05_06_08_versions_failure_and_preserve` |
| AC-RPB-09 | `test_ac_rpb_09_candidate_pool_500_stable_pages` |
| AC-RPB-10 | `test_ac_rpb_10_metrics_are_not_fabricated` plus `test_ac_rp_17_metric_filter_and_unconfigured_status` |
| AC-RPB-11 | `test_ac_rpb_11_12_contract_and_migration_are_declared` and migration backfill |
| AC-RPB-12 | temporary SQLite `upgrade -> downgrade -> upgrade`, recorded in release validation |

| AC | Behavioral test(s) |
|---|---|
| AC-RP-01 | `test_ac_rp_01_500_items_select_default_12_and_four_stages` |
| AC-RP-02 | `test_ac_rp_02_target_bounds_api` |
| AC-RP-03 | `test_ac_rp_03_deterministic_quota_redistribution` |
| AC-RP-04 | `test_ac_rp_04_selection_is_deterministic_with_stable_ties` |
| AC-RP-05 | `test_ac_rp_05_items_are_unique_and_roles_exclusive` |
| AC-RP-06 | `test_ac_rp_06_highly_relevant_is_not_public_stage` |
| AC-RP-07 | `test_ac_rp_07_missing_metrics_are_unavailable_not_zero` |
| AC-RP-08 | `test_ac_rp_08_active_plan_contract` |
| AC-RP-09 | `test_ac_rp_09_read_status_controls_read_at` |
| AC-RP-10 | `test_ac_rp_10_manual_item_requires_snapshot_membership` |
| AC-RP-11 | `test_ac_rp_11_stage_order_strict_validation` |
| AC-RP-12 | `test_ac_rp_12_full_core_requires_explicit_strategy` |
| AC-RP-13 | `test_ac_rp_13_replan_preserves_read_key_locked_and_manual` |
| AC-RP-14 | `test_ac_rp_14_replan_versions_without_overwrite` |
| AC-RP-15 | `test_ac_rp_15_generation_activation_is_atomic` |
| AC-RP-16 | `test_ac_rp_16_consolidated_excludes_only_folded_duplicate` |
| AC-RP-17 | `test_ac_rp_17_metric_filter_and_unconfigured_status`, `test_ac_rp_17_candidates_search_filter_pagination_and_total` |
| AC-RP-18 | `test_ac_rp_18_json_and_csv_exports` |
| AC-RP-19 | existing `test_reading_order.py` plus `test_ac_rp_19_legacy_reading_order_compatibility` |
| AC-RP-20 | `test_ac_rp_10_and_20_manual_item_membership_and_errors`, `test_ac_rp_20_cross_result_and_invalid_stage_are_rejected` |
| AC-RP-21 | `test_ac_rp_21_active_detail_uses_bounded_queries` |
| AC-RP-22 | migration round-trip commands and `test_ac_rp_22_metadata_matches_migration` |
| AC-RP-23 | full `pytest`, `ruff check .`, and `mypy` gates |
| AC-RP-24 | final path audit (`git diff -- frontend data/app.db`) |

## Final verification (2026-08-28)

| AC | Result | Evidence |
|---|---|---|
| AC-RP-01 | PASS | `test_ac_rp_01_500_items_select_default_12_and_four_stages` |
| AC-RP-02 | PASS | `test_ac_rp_02_target_bounds_api` |
| AC-RP-03 | PASS | `test_ac_rp_03_deterministic_quota_redistribution` |
| AC-RP-04 | PASS | `test_ac_rp_04_selection_is_deterministic_with_stable_ties` |
| AC-RP-05 | PASS | selection and persisted-plan uniqueness tests |
| AC-RP-06 | PASS | `test_ac_rp_06_highly_relevant_is_not_public_stage` |
| AC-RP-07 | PASS | `test_ac_rp_07_missing_metrics_are_unavailable_not_zero` |
| AC-RP-08 | PASS | `test_ac_rp_08_active_plan_contract` |
| AC-RP-09 | PASS | read timestamp API test and legacy-status normalization test |
| AC-RP-10 | PASS | snapshot-membership API/service tests |
| AC-RP-11 | PASS | strict validation plus persisted reverse-order readback |
| AC-RP-12 | PASS | 409, expand, and replace behavior tests |
| AC-RP-13 | PASS | default replan preservation behavior test |
| AC-RP-14 | PASS | version increment and old-version readback test |
| AC-RP-15 | PASS | simulated activation failure keeps the previous active plan |
| AC-RP-16 | PASS | consolidated duplicate projection behavior test |
| AC-RP-17 | PASS | candidate search/filter/pagination/total and metric-status tests |
| AC-RP-18 | PASS | CSV/JSON content and unsupported-format test |
| AC-RP-19 | PASS | legacy suite plus deprecated OpenAPI compatibility test |
| AC-RP-20 | PASS | 404/409/422 and cross-result/stage boundary tests |
| AC-RP-21 | PASS | active-detail and candidate-pool bounded-query tests |
| AC-RP-22 | PASS | temporary SQLite upgrade/downgrade/upgrade, Alembic check, schema and PRAGMA checks |
| AC-RP-23 | PASS (backend scope) | full pytest 815 passed/13 skipped; backend `ruff check app tests alembic` passed; project-configured mypy passed. |
| AC-RP-24 | PASS | formal database upgraded through the reading-plan revision and is now at repository head `d7e8f9a0b1c2`; consistency backups retained; no reading-plan data was generated; frontend was not modified by the activation step |

### Reproducible gate results

- Feature regression: `python -m pytest tests/modules/reading_plan tests/modules/literature_search/test_reading_order.py tests/test_database.py -q` -> 49 passed.
- Repository tests: `python -m pytest -q` -> 815 passed, 13 skipped.
- Feature-scope Ruff -> passed.
- Project-configured mypy -> success, 26 source files.
- Repository-wide `ruff check .` -> seven existing findings in `experiments/minirag/demo.py`, `experiments/paperqa2_r0/run.py`, `experiments/retrieval_baseline/run_baseline.py`, `frontend/scripts/visual-test-only/workspace_v2_diff.py`, and `scripts/r0_paperqa_demo.py`.
- Temporary migration database revision: `c6d7e8f9a0b1`; `quick_check=ok`; `foreign_key_check=[]`; `alembic check` found no new operations.
- Formal database activation (2026-08-28): consistency backup
  `data/backups/app-before-reading-plan-20260828-175440.db` retained with
  SHA-256 `1B8882DE5E117781FB2E1D1D53DBE8FD50AE4B0B3E1499DB80559914CED54722`.
  The formal database is at the unique head `c6d7e8f9a0b1`; `alembic check`
  reports no pending operations, `quick_check=ok`, and
  `foreign_key_check=[]`. Existing business-table counts were unchanged;
  `reading_plans` and `reading_plan_items` both remain empty.
- Formal-database read-only API smoke: health returned HTTP 200, the
  reading-plan route is present in OpenAPI, and a result without a generated
  plan returned the contracted HTTP 404. Key table counts were unchanged by
  the smoke test.
- Subsequent repository-head activation (2026-08-28): consistency backup
  `data/backups/app-before-recommendation-v5-20260828-222319.db` retained with
  SHA-256 `7D8108FF022107F1C81DCD1537DBE67B9B4150A5BB588D10FB58710CF3E15630`.
  The formal database was upgraded from `c6d7e8f9a0b1` to the unique head
  `d7e8f9a0b1c2`. Existing reading-plan and business-table counts were
  unchanged; `quick_check=ok`, `foreign_key_check=[]`, and `alembic check`
  reported no pending operations.
