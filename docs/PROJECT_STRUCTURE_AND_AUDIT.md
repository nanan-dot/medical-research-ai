# 项目结构与代码审查记录

## 本次审查结论

- Python 代码已使用 Ruff 统一格式化，行宽限制为 **88** 列；较长的参数、条件和调用会自动换行。
- Ruff 静态检查通过。
- Mypy 类型检查通过（当前配置覆盖 22 个源文件）。
- 核心测试：**181 passed**。
- 修复了 Windows 中文路径导致安全测试以 GBK 解码 Git 输出、从而失败的问题。测试子进程现在显式使用 UTF-8。
- 业务模块的全量测试单次运行超过当前环境的 60 秒窗口，尚需分组继续执行；该中断不代表测试失败。

## 常用检查命令

```powershell
ruff check . --fix
ruff format .

$env:PYTHONPATH=''
& 'F:\software\programme\Anaconda\envs\med-research-ai\python.exe' -m pytest -q
```

## 顶层目录和文件

| 路径 | 作用 |
| --- | --- |
| `app/` | FastAPI 后端应用源码。 |
| `alembic/` | 数据库结构迁移及其运行配置。 |
| `frontend/` | Vue 3 + TypeScript 前端。 |
| `tests/` | 后端自动化测试。 |
| `experiments/` | 可独立运行的实验原型。 |
| `scripts/` | 开发、验收和演示辅助脚本。 |
| `data/` | 本地数据库、索引和运行数据；不应提交敏感内容。 |
| `docs/` | 产品、架构、验收和开发规范文档。 |
| `.codex/` | Codex 任务提示词、前端实施计划与项目记忆。 |
| `.hermes/` | Hermes 的任务附件和检查记录。 |
| `.mypy_cache/`、`.pytest_cache/`、`.ruff_cache/` | 工具运行产生的缓存，可删除后自动再生成。 |
| `.idea/` | JetBrains IDE 本地配置。 |
| `.env` | 本机环境变量与密钥，禁止提交。 |
| `.env.example` | 环境变量模板，可安全提交。 |
| `.gitignore` | Git 忽略规则。 |
| `pyproject.toml` | Python 包、依赖、Pytest、Ruff 和 Mypy 配置。 |
| `requirements-r0.lock` | R0 环境锁定依赖。 |
| `alembic.ini` | Alembic 配置。 |
| `README.md` | 项目说明与启动方式。 |
| `AGENTS.md`、`CLAUDE.md` | AI 协作和项目开发约束。 |
| `CHANGELOG.md` | 版本变更记录。 |

## 后端 `app/`

| 路径 | 作用 |
| --- | --- |
| `main.py` | FastAPI 应用入口：注册路由、生命周期和异常处理。 |
| `core/config.py` | 环境变量和应用设置。 |
| `core/database.py` | SQLAlchemy 引擎、会话和数据库初始化。 |
| `core/models.py` | 全局 ORM 模型注册。 |
| `core/security.py` | 安全相关逻辑。 |
| `common/exceptions.py` | 领域异常定义。 |
| `common/exception_handlers.py` | 领域异常到 HTTP 响应的转换。 |
| `common/hashing.py` | 文件与内容哈希。 |
| `common/logger.py` | 日志配置。 |
| `common/path_utils.py` | 路径规范化和安全处理。 |
| `api/` | API 版本命名空间。 |
| `cli/r0_demo.py` | R0 命令行演示入口。 |

### 外部集成 `app/integrations/`

| 目录 | 作用 |
| --- | --- |
| `llm/` | 云端 LLM 客户端、配置模型和异常映射。 |
| `ollama/` | 本地 Ollama 客户端、模型状态与异常处理。 |
| `paperqa2/` | PaperQA2 索引/问答封装、工厂和数据模型。 |
| `pubmed/` | PubMed 客户端、缓存、限流、响应模型与异常。 |

每个集成目录内：`client.py` 为客户端；`schemas.py` 为数据模型；`exceptions.py` 为异常；`__init__.py` 将目录声明为 Python 包。`pubmed/cache.py` 和 `rate_limit.py` 分别实现缓存和请求限流，`paperqa2/factory.py` 负责创建适配器。

### RAG `app/rag/`

| 文件 | 作用 |
| --- | --- |
| `splitter.py` | 文档切块。 |
| `embeddings.py` | 嵌入模型适配。 |
| `faiss_store.py` | FAISS 向量索引存取。 |
| `bm25_store.py` | BM25 关键词检索。 |
| `hybrid_retriever.py` | 向量与关键词混合召回。 |
| `rrf.py` | RRF 融合排序。 |
| `vector_retriever.py` | 向量检索抽象。 |
| `notes_pipeline.py` | 笔记索引和查询流程。 |
| `schemas.py`、`exceptions.py` | RAG 数据结构与异常。 |

### 业务模块 `app/modules/`

每个业务模块中的标准文件职责相同：`model.py` 为数据库 ORM 模型；`schema.py` 为 Pydantic 请求/响应模型；`repository.py` 为数据库读写；`service.py` 为业务规则；`router.py` 为 HTTP 接口；`__init__.py` 为包声明。

| 目录 | 额外文件与领域作用 |
| --- | --- |
| `advisor_workflow/` | 导师式评审；`mock_reviewer.py` 模拟评审，`state_machine.py` 管理状态。 |
| `ai_disclosure/` | AI 使用披露；`event_normalizer.py` 规范事件，`disclosure_draft.py` 生成草稿。 |
| `citation_check/` | 引文核验；`extractor.py` 提取 DOI/PMID，`format_validator.py` 校验格式，`verifier.py` 查验文献，`statement_checker.py` 检查论断与证据。 |
| `comparison/` | 多论文比较；`shared.py` 为共享定义。 |
| `conversation/` | 文献问答；`no_answer.py` 定义无答案策略。 |
| `document/` | 文档管理、解析和索引；`index_service.py` 建索引，`matcher.py` 匹配来源，`state_machine.py` 管理任务状态。 |
| `document/parsers/` | `base.py` 解析协议，`factory.py` 创建解析器，`markdown_parser.py`/`pdf_parser.py` 解析具体格式，`schemas.py` 定义结果。 |
| `evaluation/` | 研究或模型评估记录。 |
| `evidence_analysis/` | 证据分析；`statistics.py` 统计，`interpretation.py` 受约束解释，`prompts.py` 提示词。 |
| `evidence_matrix/` | 证据矩阵；`export.py` 导出 CSV/Markdown。 |
| `evidence_writing/` | 证据写作；`sentence_marker.py` 标注句子，`polish_guard.py` 防止润色改动数字/引文，`state_machine.py` 管理流程。 |
| `export/` | 内容导出；`markdown_renderer.py` 渲染 Markdown。 |
| `feasibility/` | 研究可行性评分；`scoring.py` 执行权重计算。 |
| `feedback/` | 用户反馈。 |
| `health/` | 系统健康状态。 |
| `knowledge_source/` | 知识源管理；`scanner.py` 扫描文件，`sync_service.py` 同步来源。 |
| `library_item/` | 文献库条目管理。 |
| `literature_search/` | 文献检索：`query_builder.py` 构造查询，`pubmed_executor.py` 执行请求，`filtering.py`/`dedup.py`/`ranking.py` 处理结果，`bibtex.py` 导出引文，`reading_order.py` 管理阅读顺序，`term_expansion.py` 扩展术语，`mesh_client.py` 对接 MeSH。 |
| `model_config/` | 模型连接和隐私配置。 |
| `outline/` | 论文/汇报大纲；`outline_builder.py` 组装结构。 |
| `paper_analysis/` | 单篇论文分析与提示词管理。 |
| `presentation/` | 汇报演示稿；`outline_builder.py` 生成大纲。 |
| `recommendation/` | 研究方向推荐；`orchestrator.py` 编排，`query_builder.py` 建检索式，`reason_fusion.py` 融合推荐理由。 |
| `research_conditions/` | 研究条件；`validation.py` 负责规则校验。 |
| `research_direction/` | 研究方向生成；`generator.py` 生成候选，`prompts.py` 管理提示词。 |
| `topic_structuring/` | 课题结构化；`structure_classifier.py` 识别 PICO/PECO 等。 |
| `writing/` | 论文写作内容。 |
| `writing_project/` | 写作项目与版本；`versioning.py` 创建、恢复不可变快照。 |

## 数据库迁移 `alembic/`

`env.py` 是迁移运行环境，`versions/*.py` 中每个文件是一条按文件名描述的历史数据库结构变更，`script.py.mako` 是新迁移文件模板，`README` 为迁移目录说明。

## 测试 `tests/`

| 路径 | 作用 |
| --- | --- |
| `test_smoke.py` | 应用加载、模块导入和路由注册的冒烟测试。 |
| `test_health.py` | 健康检查接口测试。 |
| `test_database.py` | 数据库初始化与事务测试。 |
| `unit/` | LLM、Ollama、PubMed、PaperQA2、R0 演示等独立单元测试。 |
| `rag/` | 切块、嵌入、FAISS、BM25、混合召回、RRF 测试。 |
| `parsers/` | Markdown/PDF 解析测试。 |
| `security/` | 密钥泄漏、Git 忽略与安全错误脱敏测试。 |
| `modules/<领域>/` | 与同名后端业务模块对应的 API、服务和状态机测试。 |
| `integrations/` | 真实网络、Ollama 或云模型集成测试，默认不应在离线环境执行。 |
| `experiments/` | 实验原型回归测试。 |

所有 `test_*.py` 均按文件名对应被测能力；同目录的 `conftest.py` 提供该测试域共享 fixture，`__init__.py` 是包声明。

## 前端 `frontend/`

| 路径 | 作用 |
| --- | --- |
| `src/main.ts` | 前端入口。 |
| `src/App.vue` | 根组件。 |
| `src/router/` | 路由与路由元数据。 |
| `src/api/` | 每个文件对应一个后端领域 API；`client.ts` 是 HTTP 客户端。 |
| `src/types/` | 前端 TypeScript 类型。 |
| `src/views/` | 页面级组件，每个 `.vue` 文件代表一个页面或子页面。 |
| `src/components/` | 可复用 UI；文件名直接表明功能，例如 `DocumentManager.vue`、`EvidenceCard.vue`、`AppSidebar.vue`。 |
| `src/composables/` | Vue 组合式状态与逻辑，例如 `useDocuments.ts`。 |
| `src/config/` | 功能开关与边界配置。 |
| `src/mocks/` | 演示和测试用模拟数据。 |
| `src/layouts/` | 页面骨架。 |
| `src/styles/` | 全局样式。 |
| `*.test.ts` | 紧邻对应组件或模块的前端测试。 |
| `vite.config.ts`、`tsconfig*.json` | Vite 构建与 TypeScript 配置。 |

## 实验与脚本

- `experiments/minirag/`：最小 RAG 原型及示例笔记。
- `experiments/paperqa2_r0/`：PaperQA2 R0 实验、结果结构和独立依赖锁定文件。
- `experiments/retrieval_baseline/`：检索基线实验及问题集。
- `scripts/r0_paperqa_demo.py`：PaperQA 演示脚本。
- `scripts/r0_test_cloud_llm.py`：云端 LLM 连通性测试。
- `scripts/r0_test_ollama.py`：本地 Ollama 连通性测试。
