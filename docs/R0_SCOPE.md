# R0 范围与工程基线

## 目标

R0 建立可复现、可验证、可回滚的医学科研智能助手平台开发基础。本工作包仅负责范围、环境、敏感信息保护和 Git 基线，不实现业务能力。

## 当前仓库能力

- FastAPI 应用入口及 API v1 路由聚合。
- SQLAlchemy 异步会话、声明式模型基类和 Alembic 配置。
- health、model_config、knowledge_source、document、conversation、paper_analysis、literature_search、research_direction、writing、feedback、evaluation 的分层脚手架。
- 配置加载和模块导入冒烟测试。

上述模块目前是工程骨架，不表示完整 RAG、检索、写作或 Agent 流程已经交付。

## 本工作包范围

- 验证 `med-research-ai` Conda 环境、Python 3.12、pip 和项目依赖。
- 从 `.env.example` 复制本地 `.env`。
- 规定环境变量、本地数据、敏感文件和 Git 使用方式。
- 确认 `data/` 为 R0 实验数据统一目录。
- 建立 `feature/r0-wp01-baseline` 开发分支。
- 记录 R0 范围、Backlog 和实施状态。

## 明确禁止范围

- 前端页面、完整知识库业务、Obsidian 完整同步和 Mini-RAG。
- FAISS、BM25、Reranker、多向量检索和 PubMed 集成。
- 研究方向、科研写作和 LangGraph Agent 实现。
- Docker、微服务、多用户与认证实现。
- 修改数据库模型或生成迁移。
- 修改或删除用户原始论文。

## 环境变量清单

| 变量 | 用途 | R0 默认/要求 |
| --- | --- | --- |
| `DATABASE_URL` | 异步数据库连接 | 本地 SQLite：`sqlite+aiosqlite:///./data/app.db` |
| `DEBUG` | 本地调试开关 | 本地为 `true` |
| `DEFAULT_MODEL_PROVIDER` | 模型路由占位 | `openai`；R0 不发起真实调用 |
| `OPENAI_API_KEY` | OpenAI 凭证 | 留空，不提交 |
| `OPENAI_BASE_URL` | OpenAI API 地址 | 模板默认值 |
| `OLLAMA_BASE_URL` | 本地 Ollama 地址 | 模板默认值 |
| `OPENROUTER_API_KEY` | OpenRouter 凭证 | 留空，不提交 |
| `PUBMED_API_KEY` | PubMed 凭证 | 留空，不提交 |
| `PUBMED_EMAIL` | PubMed 联系邮箱 | 留空，不提交 |

`.env` 必须从 `.env.example` 复制且不得被 Git 跟踪。新增配置项时先更新 `.env.example`，只写安全占位值。

## Python 与依赖约定

本机全局 `PYTHONPATH` 受到其他环境污染。所有项目 Python 命令必须显式清空 `PYTHONPATH`：

```bash
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest
```

不得在本工作包安装、升级或删除依赖；只验证 `pyproject.toml` 声明的基础依赖可导入。

## 数据与敏感信息约定

- R0 实验数据统一放入 `data/`。
- `.env`、`data/`、数据库、索引、上传临时文件和 PDF 必须保持未跟踪。
- 不在测试、日志或响应中输出 API Key、未发表材料或完整敏感内容。
- 普通测试不得调用产生费用的真实云服务；外部服务应使用 Mock，真实集成测试需单独标记。

## Git 分支与提交约定

- 基线分支：`feature/r0-wp01-baseline`。
- 不直接在 `master` 上实施工作包。
- 提交遵循 Conventional Commits。
- 本工作包建议提交：`chore(r0): establish scope environment and git baseline`。
- 提交前必须检查工作区和忽略规则；任务资料 `.codex/` 不属于本工作包交付物，不应随本提交加入。

## 验收边界

验收包括 Python 3.12、依赖导入、现有自动化测试、Alembic 一致性检查、Git ignore 规则和分支确认。本工作包没有业务 API、前端或数据库模型变更。
