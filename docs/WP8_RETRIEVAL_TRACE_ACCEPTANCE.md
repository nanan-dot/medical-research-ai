# WP8 Retrieval Trace、审计与隐私验收追踪

## 范围说明

当前用户指令定义的 WP8 是 Retrieval Trace、审计与隐私。指定执行规格文件中的“第十部分：WP8”实际描述的是 MMR 与阅读顺序，二者存在冲突；本轮按当前用户消息（更高优先级）的明确目标实施，不执行 MMR 或 WP9。

Trace 使用应用层 JSONL，固定在 `DATA_DIR/rag_traces/` 或其受限子目录中；本轮不新增数据库表、Alembic 迁移、系统日志服务或系统级定时任务。

| AC | 验收行为 | 测试 | RED | GREEN | 状态 |
| --- | --- | --- | --- | --- | --- |
| AC-WP8-01 | Trace 保留 query plan、Profile、候选阶段、选中证据、降级原因、耗时、答案、引用、模型/提示词/索引版本 | `tests/rag/test_retrieval_trace.py::test_wp8_trace_persists_answer_candidates_and_fallbacks`、`test_wp8_trace_links_returned_answer_to_replayable_evidence` | 模块缺失，导入失败 | PASS | PASS |
| AC-WP8-02 | 答案可通过 `trace_id` 追溯选中证据和原始候选；降级原因可查询 | `test_wp8_trace_links_returned_answer_to_replayable_evidence`、`test_wp8_trace_persists_answer_candidates_and_fallbacks` | 同上 | PASS | PASS |
| AC-WP8-03 | 默认不保存 query/正文；Authorization、Cookie、API Key 等敏感字段脱敏；绝对路径仅保留文件名 | `test_wp8_trace_privacy_defaults_redact_secrets_text_query_and_absolute_paths`、`tests/rag/test_hybrid.py::test_search_writes_traceable_jsonl_log` | 同上 | PASS | PASS |
| AC-WP8-04 | 候选数量和文本长度受限；`RAG_TRACE_*` 配置校验目录与数值 | `test_wp8_trace_applies_candidate_and_text_limits`、`tests/test_rag_trace_config.py` | 同上 | PASS | PASS |
| AC-WP8-05 | 固定 Trace 的候选回放顺序按 rank + chunk_id 确定 | `test_wp8_replay_order_is_deterministic_for_fixed_trace` | 同上 | PASS | PASS |
| AC-WP8-06 | Schema 版本为 `rag-trace-v1`，旧 `RetrievalTrace(query_plan=...)` 可构造 | `test_wp8_trace_schema_is_backward_compatible` | 同上 | PASS | PASS |
| AC-WP8-07 | 保留期清理由应用层显式执行，且仅操作 `DATA_DIR/rag_traces`；旧 Hybrid JSONL 也拒绝 DATA_DIR 外路径 | `test_wp8_trace_retention_cleanup_stays_under_data_dir`、`tests/test_rag_trace_config.py::test_wp8_trace_directory_must_stay_under_data_dir`、`tests/rag/test_hybrid.py::test_trace_log_path_must_stay_under_project_trace_data_dir` | 同上 | PASS | PASS |

## 配置与兼容性

- 新增 `RAG_TRACE_ENABLED`（默认 `false`）、正文/query 开关、候选/文本上限及保留期；无启用 flag 时 `trace_store_from_settings()` 返回 `None`。
- `RAG_TRACE_DIR` 只能是 `DATA_DIR` 的子目录；不接受任意系统路径。
- 旧 `RetrievalTrace.candidates` 与 `evidence` 字段仍保留。`HybridRetriever(log_path=...)` 的旧签名仍可用，但默认 JSONL 不再写入 query、正文或绝对路径。
- 没有新增 API，因此不存在向未授权前端导出本机路径的新路由。

## 数据与效果边界

本工作包验证的是工程审计、可重放顺序和隐私最小化边界。没有真实医学金标准、真实 LLM 或真实 reranker 的效果验证；不得据此宣称医学检索、答案质量或临床安全性提升。

## 实际验证

- `$env:PYTHONPATH = ''; ...python.exe -m pytest tests/rag tests/agents/test_trace.py tests/modules/qa/test_conversation_service.py tests/modules/qa/test_grounded_conversation.py tests/modules/citation_check tests/test_rag_trace_config.py -q`：127 passed；1 个第三方 `httpx`/Starlette 弃用警告。
- `...python.exe -m ruff check app/core/config.py app/rag/schemas.py app/rag/trace.py app/rag/hybrid_retriever.py app/rag/__init__.py tests/rag/test_retrieval_trace.py tests/rag/test_hybrid.py tests/test_rag_trace_config.py`：PASS。
- `...python.exe -m mypy`（项目配置范围，26 个 source files）：PASS。
