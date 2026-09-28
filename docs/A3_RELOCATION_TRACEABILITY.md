# A3 旧资产迁移与跨版本重定位验收追踪

状态：核心实现与自动化门禁已通过；复杂版面真实 PDF、跨版本候选准确率和运维容量仍待专项验证。所有候选默认 `proposed/relocated_unverified`，V1 只有本地人工操作可确认。

| ID | Given / When / Then | 验证位置 | 状态 |
|---|---|---|---|
| A3-01 | 已确认迁移 / 解析资产 / original anchor 永不改变，resolved anchor 单独更新 | `test_models.py`, `test_api.py` | 已验证 |
| A3-02 | 同页唯一旧批注文本且几何一致 / apply 回填 / 建立 anchored_exact | `test_backfill.py` | 已验证 |
| A3-03 | 同页重复文本 / 回填 / 仅几何可消歧，否则保留多候选 | `test_backfill.py` | 已验证 |
| A3-04 | 旧文件哈希无对应 A0 / 回填 / unresolved 且旧资产仍可读 | `test_backfill.py` | 已验证 |
| A3-05 | 软删除批注 / 普通回填 / 跳过 | `test_backfill.py` | 已验证 |
| A3-06 | 无历史 file_hash 的 Citation / 任意候选 / 始终从 legacy_unversioned 开始 | `test_backfill.py` | 已验证 |
| A3-07 | 当前 PDF 唯一匹配 Citation / 生成候选 / 不自动成为 anchored_exact | `test_backfill.py` | 已验证（保守保留 `legacy_unversioned`） |
| A3-08 | 数字、单位、统计或否定表达变化 / 候选 / 标记保护表达不一致且不可确认 | `test_candidate_scoring.py`, `test_api.py` | 已验证 |
| A3-09 | 精确、上下文、页码或章节变化 / 生成候选 / 返回分项证据与有限排序 | `test_candidate_scoring.py`, `test_api.py` | 部分验证：文本与保护表达评分已测；章节/相对位置/几何分项尚未实现 |
| A3-10 | 多候选 / 生成 / 不自动选择第一个 | `test_api.py` | 已验证 |
| A3-11 | 人工确认、拒绝、撤销 / 提交 / 保存审计且不改写历史回答与资产正文 | `test_api.py` | 部分验证：确认、审计与原始锚点不可变已测；拒绝/撤销的端到端回归待补 |
| A3-12 | 两窗口提交不同候选 / expected version 过期 / 409 | `test_api.py` | 已验证 |
| A3-13 | PDF 换版 / 检测 / 旧 A0 stale、资产 relocation_required、旧快照保留 | `test_file_revisions.py` | 已验证 |
| A3-14 | dry run / 执行 / 不写 Anchor 或链接且报告不含原文/笔记 | `test_backfill.py` | 已验证 |
| A3-15 | apply 中断或重复 / 恢复 / 主键游标继续且无重复条目 | `test_backfill.py` | 已验证 |
| A3-16 | 单项坏数据 / 批次 / 记录失败并继续；系统性错误停止 | `test_backfill.py` | 部分验证：单项失败后继续已测；系统性中断与恢复报告待专项压测 |
| A3-17 | 新 Schema 独占资产存在 / downgrade / 阻止或明确不可逆警告 | `test_migration.py` | 已验证 |
| A3-18 | 无文档权限 / 候选、决策或报告读取 / 403 且不泄漏 quote | `test_api.py` | 已验证（候选读取）；决策/报告路径待补 |
| A3-19 | 候选对比 / UI / 展示旧新原文、版本、字符及保护表达差异，可确认/拒绝/暂缓 | `AnchorRelocationReview.test.ts`, `a3-relocation-review.spec.ts` | 部分验证：组件和路由 mock 浏览器流已测；真实换版 PDF 流待测 |

真实换版医学论文样本的候选准确率、SQLite 大数据量迁移耗时和旧 PDF 保留成本必须单独实测，不能由合成夹具代替。

## 本轮自动化证据（2026-08-31）

- 相关后端：`pytest tests/modules/document_relocation … tests/test_database.py -q`，150 passed。
- 静态检查：A3 及直接依赖模块的 Ruff 与 mypy 通过。
- 前端：`npm run typecheck`、`npm test -- --run`、`npm run build` 通过；构建仅保留既有的单包大于 500 kB 警告。
- 全量后端：初次结果为 1039 passed、13 skipped、3 failed；其中 A0 migration head 断言已改为动态读取当前 head，并以 `test_migration.py + document_relocation` 的 20 passed 回归确认。剩余两项失败均在并行的 `paper_library` 契约（研究关系冲突状态码、模型表清单）中，未经过 A3 代码路径。
