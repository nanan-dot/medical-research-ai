# 项目协作记忆

更新时间：2026-08-04（Asia/Shanghai）

## 项目与分支

- 仓库：`H:\AI_project\rag_medicine`
- 当前前端分支：`feature/r0-wp01-baseline`
- 前端开发服务器：`http://127.0.0.1:5173`
- 文档库页面：`http://127.0.0.1:5173/documents`

## 已完成前端阶段

- FE-01 Design System 与应用外壳：`3cf3a76`
- FE-02 工作台、知识源、文档：`d10ae09`、`27d3b37`
- FE-03 论文分析与证据问答：`9cea358`、`7bf4bc2`
- FE-04 文献检索构建器：`9794457`
- FE-05 多论文对比与证据矩阵：`2319ed4`
- FE-06 研究方向、组会与写作原型：`64c9f97`
- FE-07 任务、设置、Agent 与评测：`e64e444`
- FE-08 移动端、可访问性、构建与交付文档：`49e00e6`

## 真实能力边界

- LIVE：知识源、文档、论文分析、证据问答、检索结构化、模型配置、健康检查，以及仅限文档解析/索引状态的任务中心。
- MOCK：工作台、对比/矩阵、研究方向、组会、写作、Agent 实验室、评测中心。
- UNAVAILABLE：PubMed 结果列表、真实 Agent 运行、LangGraph、评测执行、写作项目后端、引用核验后端等。
- 严禁把 MOCK 内容伪装为真实论文、DOI、PMID、统计数据、医学结论、任务进度、评测结果或模型运行结果。
- API Key 只能输入或展示后端掩码；禁止回显完整密钥。

## 质量与视觉约定

- 前端任务必须使用 `frontend-design`；Vue 改动必须遵循 `vue-best-practices`。
- 完成每一阶段后：运行 typecheck、Vitest、build、适用 audit，并进行浏览器页面视觉核对后提交。
- 视觉风格：深海军蓝导航、浅纸色工作区、主蓝操作色、克制的证据状态色。
- 当前最终前端验证：`npm run typecheck`、`npm test -- --run`（19 passed）、`npm run build`、`npm audit --omit=dev --audit-level=high`（0 vulnerabilities）。

## 注意事项

- 工作区有大量用户未跟踪的 `.codex/`、`.hermes/`、`AGENTS.md` 与设计资料；除非用户明确要求，不能将它们加入提交。
- 本文件是本地协作记忆，不应提交到 Git，除非用户明确要求。
