# AGENTS.md — 医学科研智能助手平台

## 项目

本地优先的医学科研智能助手（医学文献检索 + 论文分析 + 证据问答 + 科研写作辅助）。
技术栈：FastAPI + SQLAlchemy + Alembic（后端） / Vue 3 + TypeScript + Vite（前端）。

## 关键环境约束（Windows）

- 工作目录：`H:\AI_project\rag_medicine`，所有操作在此目录下。
- **PYTHONPATH 被全局设为 Hermes venv**，所有 python 命令前必须加 `env PYTHONPATH=""`。
- 后端 Python：`/f/software/programme/Anaconda/envs/med-research-ai/python.exe`（Python 3.12）。
- 前端：`frontend/`，包管理器 npm。
- 数据库：SQLite（`data/app.db`），迁移用 Alembic。

## 前端开发规范（FE-00—FE-08 阶段）

- 总提示词：`docs/frontend/FRONTEND_MASTER_PROMPT_R2_WP02.md`（最高规范，必须服从）。
- 分阶段提示词：`.codex/FE-00*.md` ~ `.codex/FE-08*.md`，一次只执行一个 FE 任务。
- 视觉参考：`docs/design/医学科研智能平台界面总览.png`（不存在或无法查看时须报告，不得声称已查看）。
- 功能状态三态：LIVE（真实接口）/ MOCK（高保真演示，类型安全 Mock Adapter）/ UNAVAILABLE（待接入）。
- 当前后端进度：R2-WP02 已完成。R2-WP03 及之后、R3、R4 的能力不得补写后端、不得伪造医学数据。
- 状态文档：`docs/frontend/FRONTEND_IMPLEMENTATION_STATUS.md`。

## 通用规则

- 代码生成强制规范：`docs/CODE_STANDARDS.md`（V2.0，42 条，最高规范必须服从；.codex/CODE_STANDARDS.md 为同步副本）。
- 一个文件一个职责；API/Types/Store/Composable/View 分层；中文注释解释设计原因。
- 实际运行 typecheck / lint / test / build，未运行的命令不得声称通过。
- 不伪造论文、DOI、PMID、页码、统计数据和接口结果。
- 每轮完成当前任务后立即停止，不自动进入下一任务。
