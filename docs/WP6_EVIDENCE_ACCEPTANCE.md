# WP6 Evidence Set 验收

AC-WP6-01～08：直接/上下文分类、数字可追溯、未核验排除、冲突集、保守去重、无邻接扩展、证据不足与不同临床语义不合并，均由 `tests/rag/test_evidence_builder.py`、`test_numeric_verifier.py`、`test_evidence_acceptance.py` 覆盖。医学效果未验证。

实际验证：`pytest tests/rag tests/modules/citation_check -q` 为 89 passed；WP6 文件 Ruff 与项目配置范围 Mypy 通过。允许进入生成阶段的数字事实均经 `verified_numeric_facts` 校验，要求完整 metric/value/unit/population/source_chunk_id 绑定与存在的来源 chunk，工程可追溯率为 100%。
