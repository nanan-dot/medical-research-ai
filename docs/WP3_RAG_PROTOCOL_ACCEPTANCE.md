# WP3 RAG 统一候选协议验收追踪

| AC | 验证 |
|---|---|
| AC-WP3-01 | QueryPlan 与 Constraint 契约：`tests/rag/test_schemas.py` |
| AC-WP3-02 | 候选保留文档、块、路径、标题和原文身份 |
| AC-WP3-03 | 缺失页码为 `None`，不伪造 |
| AC-WP3-04 | RetrievalResult 通过 `to_ranked_evidence` 集中适配 |
| AC-WP3-05 | 旧 RetrievalResult 与 RAG 回归保持兼容 |
| AC-WP3-06 | 导航 API 在边界使用适配器，不泄漏外部对象 |

Schema 已先于本轮测试实现；对应测试记录为基线 PASS，不伪造 RED。医学效果未验证。
