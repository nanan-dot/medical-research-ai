# SmartRecruit 融合升级 P0 追踪报告

## 验收结论

| 验收项 | 实现位置 | 证据 | 结果 |
| --- | --- | --- | --- |
| P0-AC-01 出版年份只信任元数据 | `conditions.py` | 参考文献 2025 年不满足“近三年” | 通过 |
| P0-AC-02 RCT 不由正文关键词确证 | `conditions.py` | “不是 RCT”返回 `text_mention`；`non-randomized` 元数据返回 `metadata_mismatch` | 通过 |
| P0-AC-03 兼容旧字段并新增依据 | `schema.py`、`corpus.py` | API 同时返回 `condition_status` 与 `condition_matches` | 通过 |
| P0-AC-04 各阶段硬预算 | `budget.py`、`service.py` | 候选数不超过融合与重排候选上限，超限返回 `limited` | 通过 |
| P0-AC-05 导航独立重排开关 | `ranking.py`、`service.py` | 全局开关不会启动导航重排；故障原因码可区分 | 通过 |
| P0-AC-06 默认最小化 Trace | `trace.py` | JSONL 不保存查询、正文或绝对路径，API 返回 `trace_id` | 通过 |

## 真实验证

- `pytest tests/modules/document_navigation ... tests/test_grounded_rag_config.py -q`：142 passed。
- `pytest tests/modules/document_navigation -q`：26 passed。
- 本次范围 Ruff：通过。
- 本次范围 mypy：通过，检查 11 个源文件。
- `git diff --check`：通过，仅有工作区既有的 CRLF 提示。

仓库级 Ruff 检出 17 个其他模块的既有问题；仓库级 mypy 检出 8 个其他模块的既有问题。完整 pytest 在约 5% 时因预计耗时过长人工停止，停止前没有测试失败。P0 使用覆盖变更边界的 142 项组合回归作为发布证据。

## 运行限制

2026-09-19 已配置 `NAVIGATION_RERANK_MODEL_DIR=data/models/bge-reranker-base` 并启用导航重排。项目锁定的本地模型依赖已安装，离线 CPU 真实推理通过。棱镜检查修复了 5 秒公共阈值造成的假回退，并验证 40 条短候选在 30 秒导航阈值下以 `applied` 完成。SmartRecruit 教学资产缺少分类头，因此没有作为运行模型使用。医学标注集上的检索质量仍为【未评测】。
