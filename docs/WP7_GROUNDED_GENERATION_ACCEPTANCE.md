# WP7 Grounded Generation 验收追踪

本工作包只验证确定性的工程边界。Fake Generator / Provider 仅用于验证依赖注入、拒答、引用和持久化契约，不代表真实模型或医学问答效果。

| AC | 验收行为 | 覆盖测试 | 状态 |
| --- | --- | --- | --- |
| AC-WP7-01 | 新生成边界只消费 `EvidenceSet` | `tests/rag/test_answer_service.py` | PASS |
| AC-WP7-02 | 核心 Claim 必须绑定存在的引用；数字 Claim 绑定已核验数字事实 | `tests/rag/test_grounded_answer_acceptance.py` | PASS |
| AC-WP7-03 | `insufficient_evidence` 直接结构化拒答且不调用生成器 | `tests/rag/test_answer_service.py` | PASS |
| AC-WP7-04 | 冲突证据写入 limitations；生成或校验失败返回安全 `system_failure` | `tests/rag/test_grounded_answer_acceptance.py` | PASS |
| AC-WP7-05 | `paperqa` 默认路径不调用 grounded 依赖，原消息与引用持久化保持兼容 | `tests/modules/qa/test_conversation_service.py`、`tests/modules/qa/test_grounded_conversation.py::test_wp7_shadow_isolated_from_paperqa_result` | PASS |
| AC-WP7-06 | shadow 的 unavailable/completed/failed 旁路状态不改变 PaperQA2 答案、消息或引用 | `tests/modules/qa/test_grounded_conversation.py::test_wp7_shadow_isolated_from_paperqa_result` | PASS |
| AC-WP7-07 | grounded 模式只持久化被当前会话授权的数据库文档身份；领域 ID 不做字符串转主键 | `tests/modules/qa/test_grounded_conversation.py::test_wp7_grounded_persists_authorized_citation`、`test_wp7_grounded_rejects_invalid_citation_identity` | PASS |
| AC-WP7-08 | citation 写入失败会清理本次新增消息/引用并以安全 `ConflictError` 返回 | `tests/modules/qa/test_grounded_conversation.py::test_wp7_grounded_rollback_on_citation_save_failure` | PASS |

## 验证记录

`PYTHONPATH` 仅在测试进程中临时清空；未修改系统或持久环境配置。

- `pytest tests/modules/qa/test_grounded_conversation.py tests/modules/qa/test_conversation_service.py -q`：16 passed（2026-08-25）。
- `pytest tests/rag tests/modules/qa/test_conversation_service.py tests/modules/qa/test_grounded_conversation.py tests/modules/citation_check -q`：112 passed，1 个第三方 `httpx`/Starlette 弃用警告（2026-08-25）。
- `ruff check`（所有 WP7 生产文件与测试文件）：PASS。
- `mypy`（项目配置范围，26 个 source files）：PASS。

## 过程与发布边界

- 部分 WP7 Schema/基础服务在本轮测试补齐前已写入；对应测试以基线 PASS 记录，未人为制造 RED。
- 工程验收不构成真实 LLM、医学正确性、临床安全性或医学效果提升的证明。
- WP5 实际 reranker 仍缺真实模型资产；WP7 的新链路默认 `paperqa`，未作为默认发布链路启用。
