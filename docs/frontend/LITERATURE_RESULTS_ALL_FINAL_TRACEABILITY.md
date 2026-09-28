# 全部文献最终复刻验收追踪

执行规格：`docs/LITERATURE_RESULTS_ALL_FINAL_REPLICA_PROMPT.md`。最新范围不包含阅读计划、加入知识库或结果页 PDF 导入；公共 PDF/知识库能力保持不变。

| AC | 直接行为证据 |
|---|---|
| AC-01–04 | `ResultsView.test.ts`：最终三栏结构、真实任务标题/命中数、旧视觉与退役入口缺席 |
| AC-05–06 | `ExportMenu.test.ts`：当前筛选结果，只允许 CSV/RIS/BibTeX，明确不含 PDF，忙态防重入 |
| AC-07–10 | `ResultsView.test.ts`、`PaperResults.test.ts`：全部/已保存/重复、保存和阅读状态、真实结果字段 |
| AC-11–12 | `PaperResults.test.ts`：相关度、文章热度/被引与带年份期刊指标分区展示 |
| AC-13–14 | `ResultsFilterSidebar.test.ts`：只渲染后端支持的筛选并向服务端提交 |
| AC-15 | `PaperResults.test.ts`：分页范围、绝对序号与上下页行为 |
| AC-16–18 | `PubMedLink.test.ts`、`FulltextActions.test.ts`：安全 PubMed 外链、真实 PMCID 门控、用户触发 PMC |
| AC-19–20 | `ResultsView.test.ts`：无阅读计划/知识库/PDF 导入；公共 API 未删除，后端回归覆盖 |
| AC-21 | 1600×1000 两轮应用内浏览器截图对照；1024×768、390×844 响应式检查；`design-qa.md` |
| AC-22 | `npm run typecheck`、`npm run build`，以及前端完整 Vitest |
| AC-23 | 后端完整 pytest、迁移只读检查、任务文件 Ruff；全仓既有 Ruff 基线问题单独记录 |
