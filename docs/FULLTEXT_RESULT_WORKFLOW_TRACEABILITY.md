# 全文获取闭环 AC 追踪表

唯一规格：`docs/FULLTEXT_RESULT_WORKFLOW_EXECUTION_PROMPT.md`。

| AC | 直接行为测试 |
|---|---|
| AC-FT-01 | `tests/unit/test_pubmed_client.py::test_fetch_records_parses_full_record` |
| AC-FT-02 | `tests/unit/test_pubmed_client.py::test_fetch_records_missing_abstract_and_year_are_none`; `test_efetch_rejects_malformed_pmc_identifier_without_inference` |
| AC-FT-03 | `tests/modules/literature_search/test_pubmed_executor.py::test_execute_marks_records_verified_from_pubmed`; `tests/modules/literature_search/test_search_api.py::test_results_endpoint_returns_persisted_items` |
| AC-FT-04 | `tests/modules/literature_search/test_pubmed_executor.py::test_legacy_citation_snapshot_without_pmcid_remains_readable` |
| AC-FT-05 | `tests/modules/library/test_library_item.py::test_save_metadata_is_idempotent_and_explains_no_fulltext`; `test_idempotent_save_only_backfills_missing_pmcid`; `test_idempotent_save_rejects_different_nonempty_pmcid` |
| AC-FT-06 | `tests/modules/literature_search/test_search_api.py::test_results_get_never_calls_pmc_or_external_fulltext`; `tests/modules/literature_search/test_journal_metric_acceptance_api.py::test_hundred_item_page_uses_constant_metric_queries` |
| AC-FT-07 | `frontend/src/components/literature/FulltextActions.test.ts::AC-FT-07 only calls PMC retrieval after the user activates the PMC action` |
| AC-FT-08 | `tests/modules/library/test_official_pmc_client.py` 中身份/许可/官方URL/媒体类型/文件头/大小/SHA-256/PDF结构直接测试；`tests/modules/library/test_open_fulltext_service.py` 成功、身份不匹配、失败持久化测试 |
| AC-FT-09 | `frontend/src/components/literature/FulltextActions.test.ts::AC-FT-09 keeps PubMed available after an exact PMC failure` |
| AC-FT-10（最新范围） | `frontend/src/components/literature/FulltextActions.test.ts::AC-FT-10 current results do not offer knowledge-base or local-PDF import actions`; `frontend/src/components/PaperResults/PaperResults.test.ts::AC-FT-10 omits knowledge-base and PDF-import actions from the result rail` |
| AC-FT-11（最新范围） | 公共知识库/PDF API 不被删除或改写：`tests/modules/library/test_library_item.py::test_exact_doi_match_then_manual_link_and_unlink`; `tests/modules/knowledge_source/test_api.py` 的导入行为测试 |
| AC-FT-12 | `frontend/src/components/literature/PubMedLink.test.ts::AC-FT-12 only builds a fixed-host PubMed URL from a numeric PMID`; `FulltextActions.test.ts::AC-FT-12 and AC-FT-15...` |
| AC-FT-13 | `frontend/src/views/LiteratureSearch/ResultsView.test.ts::AC-FT-13 removes reading-plan entry and requests while keeping all, saved, and duplicate views` |
| AC-FT-14 | `frontend/src/composables/useLiteratureResults.test.ts::AC-FT-14 updates only the matching row without reloading or changing route state` |
| AC-FT-15 | `frontend/src/components/literature/FulltextActions.test.ts::AC-FT-12 and AC-FT-15 expose only trusted external links and accessible status controls` |
| AC-FT-16 | 评分/热度：`tests/modules/literature_scoring/test_scoring.py`; 期刊指标：`test_journal_metric_acceptance_api.py`; 去重：`test_dedup.py` 与 `useResultDeduplication.test.ts`; 筛选分页：`test_filters.py` 与 `useLiteratureResults.test.ts`; 保存/知识库：`test_library_item.py` 与 `tests/modules/knowledge_source/test_api.py`; 前端结果回归：`PaperResults.test.ts`, `ResultsView.test.ts`, `LiteratureFilters.test.ts` |

最终 PASS/FAIL 以本任务完成报告中的实际门禁输出为准；任何失败均不得标记全部完成。
