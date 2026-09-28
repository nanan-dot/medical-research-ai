# Recommendation reason pipeline acceptance traceability

| Criterion | Executable coverage |
| --- | --- |
| AC-RR-01 | `test_v5_service.py::test_exploration_run_uses_real_search_query_without_confirmed_intent` |
| AC-RR-02 | `test_v5_service.py::test_exploration_run_uses_real_search_query_without_confirmed_intent` |
| AC-RR-03 | `test_reason_pipeline_acceptance.py::test_ac_rr_03_fact_packet_is_versioned_and_all_visible_facts_are_traceable` |
| AC-RR-04 | `test_reason_pipeline_acceptance.py::test_ac_rr_04_base_reason_handles_covered_and_missing_abstract_without_new_claims` |
| AC-RR-05 | `test_reason_pipeline_acceptance.py::test_ac_rr_05_model_prompt_excludes_identity_and_source_text` |
| AC-RR-06 | `test_reason_pipeline_acceptance.py::test_ac_rr_06_unknown_fact_id_rejects_entire_response` |
| AC-RR-07 | `test_reason_pipeline_acceptance.py::test_ac_rr_07_new_number_or_entity_rejects_entire_response` |
| AC-RR-08 | `test_reason_pipeline_acceptance.py::test_ac_rr_08_medical_overclaim_rejects_entire_response` |
| AC-RR-09 | `test_reason_pipeline_acceptance.py::test_ac_rr_09_required_limitation_must_be_bound_in_limitation_section` |
| AC-RR-10 | `test_v5_reason_generator.py::test_llm_failure_retains_deterministic_reason` |
| AC-RR-11 | `test_v5_reason_generator.py::test_valid_llm_wording_can_only_replace_wording_fields` |
| AC-RR-12 | `test_v5_service.py::test_bound_run_is_idempotent_and_decision_and_explanation_are_persisted`; `test_v5_resilience.py::test_narration_lease_allows_one_claim_and_caches_terminal_fallback` |
| AC-RR-13 | `test_v5_resilience.py::test_startup_recovery_requeues_queued_and_reclaims_running` |
| AC-RR-14 | `RecommendationsView.test.ts::keeps the active list interactive while narration is pending`; `RecommendationsView.test.ts::discloses a mixed narration fallback while retaining the active list` |

The deterministic unit tests deliberately execute without a configured language model.
