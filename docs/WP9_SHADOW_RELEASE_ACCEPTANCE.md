# WP9 Shadow 验证与发布门验收追踪

## 事实基线

- WP5 已有项目目录内的实际 CPU CrossEncoder；真实模型效果仍未由医学金标准验证。
- 没有真实 Grounded Generator、医学专家金标准或冻结生产延迟预算。
- `GROUNDED_RAG_ENABLED=false`、`GROUNDED_RAG_MODE=paperqa` 是当前默认；本轮不进入默认发布阶段。

| AC | 验收行为 | 测试 | RED | GREEN | 状态 |
| --- | --- | --- | --- | --- | --- |
| AC-WP9-01 | 同一 `trace_id` 比较 BM25、Dense、Hybrid+RRF、Reranker、Grounded、PaperQA2；缺少资产明确 unavailable | `tests/rag/test_shadow_release.py::test_wp9_comparison_uses_same_trace_and_marks_missing_assets_unavailable` | `shadow_release` 模块缺失，导入失败 | PASS | PASS |
| AC-WP9-02 | shadow 或 feature flag 关闭时用户可见路径保持 PaperQA2 | `test_wp9_shadow_and_disabled_flag_preserve_paperqa_visible_mode`、`tests/modules/qa/test_grounded_conversation.py` | 同上 | PASS | PASS |
| AC-WP9-03 | 单策略失败隔离，不写入问题/文献正文到比较报告 | `test_wp9_strategy_failure_is_isolated_and_report_contains_no_question_text` | 同上 | PASS | PASS |
| AC-WP9-04 | Feature flag 默认关闭；默认构造器保持 PaperQA2 | `tests/test_grounded_rag_config.py::test_wp7_defaults_to_paperqa`、QA 回归 | 配置字段此前不存在，基线 PASS 例外：字段实现先于本轮测试 | PASS | PASS |
| AC-WP9-05 | Release Gate 仅依据冻结报告与硬门，不以单个样本决定 | `test_wp9_release_gate_refuses_default_release_when_hard_evidence_is_missing`、`test_wp9_release_gate_requires_all_frozen_hard_gates` | 同上 | PASS | PASS |
| AC-WP9-06 | 缺任一硬门时 `release_eligible=false` 并列出缺口 | `test_wp9_release_gate_refuses_default_release_when_hard_evidence_is_missing` | 同上 | PASS | PASS |

## 当前发布判定

当前事实输入到 `ReleaseEvidence` 后为 `release_eligible=false`。硬门缺口：医学专家金标准、冻结生产延迟预算、冻结的真实 Shadow 比较报告；实际 Grounded Generator 的医学质量也未验证。

Fake 策略只验证协议和故障隔离，不代表任何医学效果、模型能力、延迟 SLA 或上线资格。

## 真实本地 Shadow 工程记录（2026-08-25）

- 比较关联键：本轮工程样例使用既有 Trace 协议；未持久化问题/原文，未将样例输出当医学金标准。
- 固定 CrossEncoder 实测：revision `2cfc18c9415c912f9d8155881c133215df768a70` 的 safetensors 为 1,112,206,140 字节、202 个 tensor 键。相同公开合成样例的分数为 sotorasib 直接证据 `0.9484944`、adagrasib 背景 `0.2236650`；首次 `8,189.3ms`，warm `n=3` P50 `43.6ms` / P95 `44.5ms`。不构成医学效果或生产 SLA 证明。
- 发布仍不合格：缺医学专家金标准、冻结生产延迟预算与冻结真实 Shadow 比较报告。默认仍为 PaperQA2。

## 实际验证

- `$env:PYTHONPATH = ''; ...python.exe -m pytest tests/rag tests/modules/evaluation tests/agents/test_trace.py tests/modules/qa/test_conversation_service.py tests/modules/qa/test_grounded_conversation.py tests/modules/citation_check tests/test_grounded_rag_config.py tests/test_rag_trace_config.py -q`：156 passed；1 个第三方 `httpx`/Starlette 弃用警告。
- `...python.exe -m ruff check app/rag/shadow_release.py app/rag/__init__.py app/core/config.py app/modules/conversation/service.py tests/rag/test_shadow_release.py tests/test_grounded_rag_config.py`：PASS。
- `...python.exe -m mypy`（项目配置范围，26 个 source files）：PASS。
