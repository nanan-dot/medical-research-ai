# A1 版面、段落、章节与阅读顺序追踪报告

日期：2026-08-31。A1 只读取 A0 已发布的 `DocumentAnchorRevision`、`DocumentSourcePage` 与 `DocumentSourceTextItem`；不修改 A0 原文、规范化文本或哈希。

## 架构与接口

新增 `document_layout` 派生层：纯函数 `algorithm.py` 负责行、栏、块、跨页段落和标题；`service.py` 负责授权、读取 A0、单事务发布；持久化保存 revision、block、section、segment 和 fragment。分段身份由 A0 extraction fingerprint、算法版本、配置 hash 和输出 hash 生成。失败前没有普通读取 API 可见数据。

- `POST /api/v1/document-anchor-revisions/{id}/segmentations`
- `GET /api/v1/documents/{id}/segmentation-manifest`
- `GET /api/v1/documents/{id}/source-segments?page=12`
- `GET /api/v1/source-segments/{id}`
- `GET /api/v1/documents/{id}/sections`
- `GET /api/v1/documents/{id}/sections/{section_id}/segments`

示例：`POST /api/v1/document-anchor-revisions/42/segmentations`，携带 `Idempotency-Key`。任务使用 `document_layout_segmentation` 与 `segment:{anchor_revision_id}:{request_fingerprint}` 键；worker 以现有 TaskRepository 租约领取，完成后才置为 succeeded。

## 验收追踪

| ID | Given / When / Then | 测试 | 状态 |
|---|---|---|---|
| A1-01 | 同输入、同版本运行两次 → 相同 key 与顺序 | `test_double_column_order_is_column_major_and_deterministic` | PASS |
| A1-02 | 双栏输入 → 左栏完整后再右栏 | 同上 | PASS |
| A1-03 | 跨页未终止正文 → 一个 segment、两个有序 item 范围 | `test_cross_page_paragraph_keeps_ordered_item_ranges` | PASS |
| A1-04 | 重复页眉页脚 → 可审计 block、默认正文流排除 | `test_header_footer_are_auditable_but_not_normal_body_segments` | PASS |
| A1-05 | 标题、表题、参考文献 → 保守类型与章节角色 | `test_heading_sections_and_conservative_special_classification` | PASS |
| A1-06 | 已发布 A0 revision → A1 发布后可分页/回溯，A0 原项不变 | `test_published_layout_is_queryable_and_preserves_a0_items` | PASS |
| A1-07 | queued A1 task → 领取、续租 fencing、原子发布后成功 | `test_worker_claims_and_publishes_one_queued_layout` | PASS |
| A1-08 | transient worker failure → 有限重试队列，未发布 revision 保持 pending | `test_worker_requeues_transient_failure_with_no_publication` | PASS |
| A1-09 | 两个 worker 并发领取一个 queued task → 仅一个发布并成功 | `test_concurrent_workers_claim_one_layout_task` | PASS |
| A1-10 | A0 PDF.js 真实提取输出持久化后 → A1 可发布并读取 segments | `test_real_a0_pdfjs_output_can_publish_a1_segments` | PASS |
| A1-11 | 同页相邻章节 → 前一章节 API 不混入下一章节 Segment | `test_section_segments_do_not_leak_into_next_same_page_section` | PASS |

## 实测命令

- A1 测试先行 RED：`pytest tests/modules/document_layout/test_acceptance.py -q` → `ModuleNotFoundError`（模块尚未创建）。
- GREEN：`pytest tests/modules/document_layout -q` → **12 passed、1 warning**（最后一次 14.60 秒）。
- `ruff check app/modules/document_layout tests/modules/document_layout ...` → `All checks passed`。
- `compileall -q app/modules/document_layout` → exit 0。
- `alembic upgrade head` → `a2f8e7d6c5b4 (head)`；随后 `alembic check` → `No new upgrade operations detected.`
- A0 专项回归：`pytest tests/modules/document_anchor -q --junitxml=work/a1-a0-regression-final.xml` → **87 passed**，80.521 秒。迁移测试已将预期 head 从 A0 的 `e14d8a06c923` 前移为 A1 的 `a2f8e7d6c5b4`，同时仍验证 upgrade/downgrade/upgrade 与 sentinel 数据保留。
- 首次后端全量回归：`pytest -q --junitxml=work/a1-backend-full.xml` → 1002 tests、13 skipped、1 failure（`tests/test_database.py` 未登记 A1 的 5 张新表）。已补齐登记。最终重跑：`pytest -q --junitxml=work/a1-backend-full-final-2.xml` → **989 passed、13 skipped、1 warning，711.77 秒**；JUnit 为 1002 tests、0 failures、0 errors、13 skipped、711.147 秒。此全量回归后仅新增测试与本报告，不含生产代码变更；新增测试已由上面的 11 项 A1 专项回归覆盖。
- 章节边界修正后的最终全量回归：`pytest -q --junitxml=work/a1-backend-full-after-section-boundary.xml` → **992 passed、13 skipped、1 warning，717.28 秒**。

## 风险与未实测

- 【未实测】真实 A0 医学 PDF 的端到端 worker 运行、三栏/旋转/扫描/OCR、复杂表格、脚注密集版面和人工标注准确率。
- 已用 A0 的受控 PDF.js 提取器在 `complex.pdf`（4 页/43 TextItems）和开放医学样本 `plos-1004416.pdf`（24 页/2542 TextItems）上实际运行 A1 纯算法；后者产生 393 blocks、236 segments、67 sections。`complex.pdf` 的真实 PDF.js 输出还已持久化为 A0 页和 TextItem，再经 A1 service 发布并读取 segment（A1-10）；该验证不等价于完整 worker/API 链路。
- 取消与显式重试已由 `test_cancel_and_retry_never_publish_partial_layout` 覆盖；单 worker 领取、lease fencing、心跳与发布由 `test_worker_claims_and_publishes_one_queued_layout` 覆盖；临时失败自动重入队由 `test_worker_requeues_transient_failure_with_no_publication` 覆盖；双 worker 并发领取由 `test_concurrent_workers_claim_one_layout_task` 覆盖。
- A0 专项在当前源码下已实际通过（87 passed）；后端全量回归也已实际通过（989 passed、13 skipped）。
- A0 页面已有技术质量标记时，A1 将对应 segment 降为 `review_required`；扫描/OCR/低文本层标记降为 `blocked`，并由 `test_a0_scan_quality_blocks_derived_translation_flow` 覆盖。复杂表格的可靠区域重建仍为【未实测】。
