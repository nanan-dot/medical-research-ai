# SmartRecruit 融合升级 P0 验收标准

本阶段只处理会影响医学结论可信度和线上可观测性的基础问题，不引入数据库迁移、持久化向量索引或父子分块。

| 编号 | 验收行为 | 自动化证据 |
| --- | --- | --- |
| P0-AC-01 | “近三年”只读取受信任的出版年份元数据；参考文献或正文中的年份不得被当成出版年份 | `test_reference_year_does_not_satisfy_publication_period` |
| P0-AC-02 | RCT 条件只由结构化研究类型元数据判定；“本研究不是 RCT”不得标成事实成立 | `test_negated_rct_text_is_only_a_text_mention` |
| P0-AC-03 | API 保留旧 `condition_status`，同时返回带依据来源的新 `condition_matches` | `test_navigation_reports_structured_condition_matches` |
| P0-AC-04 | 导航候选预算使用独立配置，并显式报告 `within_budget` 或 `limited`，不得偷偷扩大 Top-K | `test_navigation_budget_never_exceeds_configured_caps` |
| P0-AC-05 | 重排开关独立于全局 RAG 开关；缺失模型与无效分数返回稳定的结构化原因码 | `test_global_rerank_flag_does_not_enable_navigation`、既有重排回退测试 |
| P0-AC-06 | 开启 Trace 后返回 `trace_id`；默认策略不持久化查询原文、正文和绝对路径 | `test_navigation_trace_is_minimized_by_default` |

发布门槛：上述测试及既有 document-navigation、RAG 回归通过；Ruff 与 mypy 通过。真实本地重排模型运行检查单独记录，模型资产或可选依赖缺失时必须报告为未就绪，不能伪装成功。
