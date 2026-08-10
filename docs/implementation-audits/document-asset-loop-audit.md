# 素问文档资产闭环：阶段 0 全仓审计与设计冻结

审计日期：2026-08-10  
审计范围：`H:\AI_project\rag_medicine`  
阶段状态：**完成审计与设计冻结；未开始阶段 1 业务实现。**

## 1. 审计边界、方法与工作区状态

本报告遵循任务文件、`AGENTS.md` 与 `docs/CODE_STANDARDS.md`。阶段 0 只新增本审计文档及对应的用户报告；没有修改任何业务代码、数据库、依赖、路由或前端页面。

已完整阅读的规范与配置：

- `AGENTS.md`；
- `docs/CODE_STANDARDS.md`；
- `docs/frontend/FRONTEND_MASTER_PROMPT_R2_WP02.md`（1,322 行）；
- `.codex/FE-00_仓库审查与前端实施计划.md`、`FE-01_Design_System与应用外壳.md`、`FE-02_工作台知识源文档模块.md`、`FE-08_移动端测试Build与文档.md`；
- `docs/frontend/FRONTEND_IMPLEMENTATION_STATUS.md`；
- `pyproject.toml`、`frontend/package.json`、`frontend/vite.config.ts`、`.env.example`、`alembic.ini`、`alembic/env.py` 与迁移历史。

已使用 `rg --files` 建立主清单（默认排除 Git 忽略文件），再单独使用 `rg --files -uu .codex` 纳入隐藏的 Codex 提示词。主清单为 678 个文件，其中 448 个 Python 文件、146 个 Vue/TypeScript 文件；`.codex/` 另有 53 个指令/记忆文件。按任务要求分组的清单计数为：

| 分组 | 文件数 | 审计结论 |
|---|---:|---|
| `app/` | 282 | FastAPI、领域模块、集成和 RAG 实现；已逐项审阅文档、知识源、索引、会话、任务、文献检索/本地库及其依赖边界。 |
| `frontend/src/` | 148 | Vue 3 前端；已逐项审阅文档 API/composable/组件/详情页/路由、功能标记及文献结果保存入口。 |
| `tests/` | 119 | 已审阅文档、解析器、索引、知识源、库条目、任务、PubMed、PaperQA2 与安全测试。 |
| `alembic/` | 39 | 已审阅环境、当前 head、文档/知识源/索引/库条目/任务/检索相关迁移，并实际核对历史与数据库。 |
| `docs/` | 55 | 已审阅编码、前端、架构与实施状态相关文档；其余领域文档按目录纳入清单。 |
| 根目录与配置 | 35 | 已审阅清单中与运行、依赖、迁移、测试有关的配置。 |
| `.codex/` | 53 | 已列出全部文件；对本任务相关的 FE-00/01/02/08 与代码规范进行了全文审阅。 |

“全仓审计”在此是架构、数据流、边界、配置与测试覆盖审计；本报告不把“仅看到文件名”等同于“逐行读完所有 448 个 Python 文件”。与五项功能无直接耦合的模块按职责和文件数归档；直接影响设计冻结的文件已逐文件审阅。

审计开始前工作区已有 8 个未提交的前端改动：`AppTopbar.vue`、`features.ts`、文献检索 History/Results/View/WorkspaceTabs 及相关测试、`RecommendationsView.vue`。这些均不属于本阶段，未被改写。

## 2. 目录、模块职责与关键路径

### 2.1 后端目录

| 路径/模块 | 职责 | 与本任务的关系 |
|---|---|---|
| `app/main.py`、`app/api/v1/__init__.py` | 应用生命周期、CORS、统一 `AppError` 响应、`/api/v1` 路由聚合。 | 新路由必须在独立领域 router 后由此聚合；当前启动仅创建 `DATA_DIR`，尚未创建 `UPLOAD_DIR`。 |
| `app/core/` | Pydantic Settings、异步 SQLAlchemy engine/session、集中模型注册、密钥加密。 | 已有 `UPLOAD_DIR=./uploads`、SQLite async 会话和 Alembic 模型注册模式。 |
| `app/common/` | `AppError`/404/409/403/503、统一错误 JSON、流式 SHA-256、路径归一化/根目录包含检查。 | `sha256_file()` 按 1 MiB 分块，可复用；上传、预览必须补齐对最终 resolved path 的强制包含检查。 |
| `app/modules/knowledge_source/`（8 个 Python 文件） | 授权目录、同步、递归扫描、来源记录。 | 扫描器已阻断越根符号链接并规范化路径；`temporary_import` 是现有来源枚举，可用于上传资产。 |
| `app/modules/document/`（16 个 Python 文件） | Document 记录、解析、状态机、PaperQA2 索引、重试与删除。 | 五项功能的主要聚合点，但上传/预览/批注/OCR 不能堆入现有 router/service。 |
| `app/integrations/paperqa2/` | 将阻塞的 PaperQA2 操作放入线程，统一索引/问答契约。 | 上传/OCR 后的解析内容要让索引显式标为过期；不能宣称自动重建成功。 |
| `app/modules/conversation/` 与 `app/rag/` | 已索引 Document 的证据问答和本地检索。 | 对话只接受当前索引成功的 `document_id`，证据引用可记录页码；OCR 成功后的再索引必须保持这一前提。 |
| `app/integrations/pubmed/` 与 `app/modules/literature_search/` | 官方 E-utilities 检索、ESearch/EFetch 元数据、检索快照。 | 当前仅取元数据、摘要和 PMC 信号；没有下载/许可验证/全文服务。 |
| `app/modules/library_item/` | 文献结果保存、本地 Document 精确匹配、全文状态展示。 | 目前 `open_access_available` 是枚举值，不能等同“本地可用”；需要独立 PMC 获取记录。 |
| `app/modules/task/`（6 个 Python 文件） | `task_records` 的持久化展示 API。 | 记录可显示任务，但没有工作队列或执行器；OCR 必须新增真实运行器。 |

其余领域模块（顾问工作流、AI 披露、引文核验、比较、评测、证据矩阵、导出、可行性、反馈、健康、模型配置、提纲、论文分析、演示、推荐、研究条件/方向、主题结构、写作）已按模块清单登记，不改变本设计冻结。

### 2.2 前端目录

| 路径 | 当前职责 | 阶段 1—5 的复用点 |
|---|---|---|
| `frontend/src/api/documents.ts` | `/documents` 的列表、详情、解析、索引、批量索引请求与 TypeScript 契约。 | 扩展为上传/预览/OCR/批注 API；不在页面直接 `fetch`。 |
| `frontend/src/composables/useDocuments.ts` | 文档分页、筛选、重试与列表状态。 | 上传成功后调用真实 `load()`；避免伪进度。 |
| `frontend/src/components/document/` | `DocumentManager`、筛选、表格和 Vitest 覆盖。 | 在 `DocumentManager` 增加独立上传入口；PDF/批注阅读器应另建组件。 |
| `frontend/src/views/Documents/DocumentDetailView.vue` | 当前只显示元数据和解析摘要，明确标注原文预览和打开原文件未接入。 | 阶段 2 需拆为详情容器、预览、元数据与行动组件；阶段 3 的 PDF.js 只在此处启用。 |
| `frontend/src/router/index.ts` | `/documents`、`/documents/:id` 已存在且懒加载。 | 无需新顶级路由；复用详情路由。 |
| `frontend/src/api/literatureSearch.ts`、`components/PaperResults/`、`components/SaveToLibrary/` | 检索结果、本地收藏、`fulltext_status` 显示。 | 阶段 5 在此加入“获取开放全文”受控入口与真实状态，不写“下载 PubMed 全文”。 |
| `frontend/src/config/features.ts`、`layouts/AppShell.vue` | LIVE/MOCK/UNAVAILABLE 边界、应用壳、无障碍基础。 | 五项新增的异步状态必须使用真实 API 状态且保持键盘/减少动画支持。 |

## 3. 现有数据库、迁移、存储、任务与错误模型

### 3.1 迁移与实际数据库

- `alembic current` 与 `alembic heads` 均为单一 head：`f6a7b8c9d0e1`。
- `data/app.db` 存在（442,368 bytes），实际包含 `documents`、`knowledge_sources`、`library_items`、`task_records`、`literature_search_tasks/results` 等 48 张表。
- 相关演进：`b741bb1a6d5c`（知识源）、`c824d91e7a30`（增量同步）、`d935e02f8b41`（文档状态）、`e146f13a9c52`（解析结果）、`f257a24b0d63`（PaperQA2 映射）、`f5a6b7c8d9e0`/`ee5f23856af4`（库条目）、`d4e5f6a7b8c9`（任务记录）。

### 3.2 现有模型

| 模型/表 | 已有字段和状态 | 缺口 |
|---|---|---|
| `Document` / `documents` | 知识源、相对路径、SHA-256、大小、修改时间、解析/索引状态、错误、解析 JSON、扫描标记、页面数、PaperQA2 映射。 | 无原文件名、媒体类型、内部资产路径、上传/获取来源、许可证、OCR 运行/输出、批注或安全预览元数据。 |
| `KnowledgeSource` / `knowledge_sources` | 规范化根目录、`local_folder`/`obsidian_vault`/`temporary_import`、可用状态和同步摘要。 | 无内部上传源的固定初始化约定。 |
| `TaskRecord` / `task_records` | `pending/running/succeeded/failed/cancelled/awaiting_confirmation`、进度、来源、错误与时间。 | 只有 CRUD 展示，当前没有队列、执行器、取消/重试调度或 OCR 专属审计字段。 |
| `LibraryItem` / `library_items` | PMID、DOI、元数据、关联 `document_id`、`metadata_only/local_pdf_available/open_access_available/unavailable`。 | 无 PMCID、许可证、来源 URL、下载时间、校验哈希、失败分类或全文获取尝试记录。 |
| 错误响应 | `{"error":{"code", "message"}}`，有 400/403/404/409/503 领域错误。 | 上传需要受限的 4xx 细分；预览、哈希冲突、OCR、PMC 适配器需新增稳定错误码。 |

### 3.3 存储现状与安全结论

- 配置根：`DATA_DIR=./data`、`UPLOAD_DIR=./uploads`、`PAPERQA_INDEX_DIR=./data/paperqa_index`、`EXPORT_DIR=./data/exports`。`.env.example` 没有上传大小或 OCR/PMC 参数。
- `UPLOAD_DIR` 已配置且 `python-multipart` 已声明，但没有上传 router/service/前端。应用启动没有创建它。
- 知识源扫描器对每个目录项执行 `resolve(strict=True)`、`is_within_root()`、相对路径/大小/修改时间记录，能够发现符号链接越界；同步通过分块 SHA-256 写入 Document。
- `DocumentService._source_file_path()` 直接拼接 `Path(source.root_path) / entity.file_path` 后检查 `is_file()`；对当前由扫描器写入的路径可工作，但它不是可公开复用的安全流式文件解析器。阶段 2 不得直接用它服务任意文件，必须先 `resolve()` 并对已解析根目录做 `relative_to()` 校验。
- `.gitignore` 及 `tests/security/test_r0_security.py` 已覆盖 `uploads/`、`data/`、PDF、数据库、日志和密钥不被跟踪；该测试是上传资产的良好基础。

## 4. 真实文档、索引、RAG 与文献数据流

```text
授权目录
  -> KnowledgeSourceService（目录授权与规范化）
  -> KnowledgeSourceSyncService / scanner（安全扫描、相对路径、SHA-256）
  -> Document（pending）
  -> DocumentService.parse（在 asyncio.to_thread 中选择 PDF/MD/DOCX/PPTX/DOC 解析器）
  -> parsed_content / parsed_is_scanned / parsed_page_count，index_status=outdated
  -> DocumentIndexService（源文件哈希复核）
  -> PaperQA2 adapter（线程隔离）
  -> 当前 PaperQA2 映射与索引状态
  -> ConversationService（只允许索引成功的 document_id）
  -> Citation（document_id、页码、章节、证据片段）

PubMed ESearch + EFetch
  -> PubMedExecutor（真实元数据/摘要/PMCID 信号）
  -> LiteratureSearchResult 快照
  -> LibraryItemService（精确 PMID/DOI 本地匹配）
  -> metadata_only 或 local_pdf_available
```

解析器和限制：

- PDF：`pypdf.PdfReader` 提取一基页码文本、去除重复页眉页脚、以极低非空文本判定扫描件；不会 OCR、不会提供 PDF 字节流。
- DOCX：`python-docx` 提取段落、标题和表格为文本；没有 HTML 预览转换器。
- DOC：仅在 `antiword`/`catdoc`/LibreOffice 可用时转本地文本；本机审计发现三者均不存在，因而不能承诺 DOC 预览。
- PPTX：只提取文字；不在预览功能范围内。
- 文件大小：解析上限 100 MiB、抽取文本上限 10,000,000 字符。上传的更严格限额应独立配置，不能借用解析上限而不做流式大小控制。

## 5. 五项功能的现状、可复用点、缺口和风险

| 功能 | 已有真实能力 | 必须新增 | 主要风险/冻结结论 |
|---|---|---|---|
| 1. 单 PDF 上传 | `UPLOAD_DIR`、`python-multipart`、Document/KnowledgeSource、分块 SHA-256、`temporary_import` 枚举。 | 独立 upload schema/router/service；单文件流式落盘、MIME+`%PDF-`+结构校验、临时文件清理、内部资产记录、上传 UI/测试。 | 不能以原文件名落盘，不能依赖扩展名或请求 Content-Type。上传成功只创建 `pending` 文档，不暗示已解析或已索引。 |
| 2. PDF/Word 预览 | PDF/DOCX/DOC 文本解析器、`/documents/:id` 和文档详情页面。 | 按 document id 的安全解析/流端点、PDF Range 支持、DOCX 受控 HTML 预览、详情预览组件与测试。 | 不接收任意本机路径；不会在 Vue 用 `v-html` 渲染原 Office 内容；DOC 在当前环境应显示不支持。 |
| 3. PDF 划线批注 | PDF 页码解析、Document `file_hash`、详情路由。 | 批注模型/迁移/API、hash 冲突、PDF.js 阅读文本层、选区几何、侧栏和 E2E。 | 目前没有 `pdfjs-dist`；批注只能启用于本地成功解析的 PDF，旧 hash 必须失效而不可静默迁移。 |
| 4. 扫描 PDF OCR | `parsed_is_scanned` 启发式、`TaskRecord`、`asyncio.to_thread` 模式、索引过期状态。 | OCR 运行/页表、独立服务与 worker、引擎适配器、输出安全目录、取消/重试、真实页级状态和前端。 | 本机没有 `tesseract`、`pytesseract`、PyMuPDF、LibreOffice 或 Poppler 安装；只发现 Codex 运行时的 `pdftoppm.cmd`，不能当作产品部署依赖。无引擎时必须明确不可用，不能伪装通过。 |
| 5. 合法开放全文 | PubMed 官方 E-utilities、PMCID 信号、速率限制/重试、LibraryItem 及本地 Document 关联。 | PMCID 保存、独立 PMC OAI-PMH 适配器/服务/router、许可验证、获取审计、受控落盘、状态/前端/模拟测试。 | PubMed 不是全文下载服务；现有 `is_open_access` 仅是 EFetch PMCID 信号，`open_access_available` 绝不能写成已下载。禁止抓取 PMC/期刊普通网页。 |

## 6. 设计冻结：分层、数据和 API

### 6.1 固定的模块边界

后续每项能力采用独立文件夹、router、service、repository、schema，避免把逻辑加入 `app/modules/document/router.py`：

```text
app/modules/document_upload/       # 阶段 1：入站文件校验、临时落盘、Document/Asset 事务
app/modules/document_preview/      # 阶段 2：安全路径解析、PDF 流、Word 受控预览
app/modules/document_annotation/   # 阶段 3：版本锚定批注
app/modules/document_ocr/          # 阶段 4：OCR 状态、队列 worker、引擎适配器
app/integrations/pmc/              # 阶段 5：仅官方允许的 PMC OAI-PMH/受控下载适配器
app/modules/fulltext_retrieval/    # 阶段 5：业务审计、LibraryItem/Document 关联和状态
```

前端沿用现有 API/composable/component/view 分层；新增上传、预览、PDF 阅读器、批注侧栏、OCR 状态及全文获取按钮必须是单一职责组件。`DocumentDetailView.vue` 当前压缩为一个 13 行文件，阶段 2 前应仅做结构性拆分，不重写无关的应用壳或文献检索页面。

### 6.2 固定的数据模型与迁移顺序

1. **阶段 1：** 新建 `document_assets`。一条受控资产关联一个 Document，保存 `asset_kind`（`upload`/`pmc_fulltext` 等）、`original_filename`、`stored_relative_path`、`media_type`、`byte_size`、`sha256`、`source_url`、`license`、`retrieved_at`、`created_at`。上传 Document 归属由服务端创建/复用的 `temporary_import` KnowledgeSource，物理文件名为服务端 UUID，相对路径必须位于 `UPLOAD_DIR` 内。
2. **阶段 3：** 新建 `document_annotations`：`document_id`、`file_hash`、`page_number`、`selection_geometry_json`、`selected_text`、`selected_text_hash`、`color`、`note`、`created_at`、`updated_at`、`deleted_at`。不含虚构作者字段。
3. **阶段 4：** 新建 `ocr_runs` 和 `ocr_pages`。run 记录 document/file hash、关联 task、状态、引擎和版本、语言包、页数、开始/完成时间、失败摘要、输出路径与输出 hash；page 记录页码、状态、输出文本和仅在引擎真实给出时的置信度。原 PDF 不变。
4. **阶段 5：** 为 `library_items` 增加 `pmcid`，新建 `fulltext_retrievals` 逐次记录 `library_item_id`、PMCID、官方来源 URL、许可、请求/完成时间、状态、失败分类、内容 hash、资产/Document 关联。只有文件落盘和校验成功后才把库条目更新为本地可用。

每个步骤均为独立 Alembic revision；不使用 `create_all()` 作为生产迁移。每张新表的状态枚举由 Pydantic schema 与迁移检查约束共同定义，失败记录也必须持久化以避免错误的成功外观。

### 6.3 固定 API 草案

| 阶段 | API | 真实行为空间 |
|---|---|---|
| 1 | `POST /api/v1/document-uploads`（multipart `file`） | 只接受一个 PDF；返回真实的 Document/Asset 元数据和 `pending` 解析状态。 |
| 2 | `GET /api/v1/documents/{id}/preview`、`GET /api/v1/documents/{id}/preview/content` | 只按 id；PDF 使用 `application/pdf`、`inline`、`nosniff`、Range；DOCX 是服务器转义后生成的只读 HTML；不支持格式返回明确描述。 |
| 3 | `GET/POST /api/v1/documents/{id}/annotations`，`PATCH/DELETE /api/v1/documents/{id}/annotations/{annotation_id}` | 创建请求必须带当前 file hash；hash 不符返回 409。 |
| 4 | `GET /api/v1/documents/{id}/ocr-eligibility`，`POST /api/v1/documents/{id}/ocr`，`GET /api/v1/documents/{id}/ocr-runs`，`POST /api/v1/ocr-runs/{id}/retry|cancel` | 入队即返回真实 queued run，耗时 CPU/进程工作不在请求协程执行。 |
| 5 | `POST /api/v1/library-items/{id}/fulltext-retrievals`，`GET /api/v1/library-items/{id}/fulltext-retrievals` | 文案和接口语义均为“获取开放全文”；无 PMCID/许可/官方服务条件时返回真实拒绝或失败状态。 |

### 6.4 固定安全实现规则

- 上传以 `UploadFile` 分块写入位于 `UPLOAD_DIR/.tmp` 的 UUID 临时文件；在 `content_type` 白名单、`%PDF-` 魔数、非空/大小上限和 `pypdf` 结构校验均通过后，原子移动至受控 UUID `.pdf` 目标。任何失败都删除临时文件且不创建 Document/Asset。
- 请求头 MIME 只能作为多重校验的一项，不能被单独信任。Windows 不引入依赖 native `libmagic` 的 MIME 探测；阶段 1 使用客户端 MIME、一致扩展名、PDF 魔数和解析器结构校验的合取。
- 新建集中式只读资产解析器：对根目录与候选路径分别 `resolve(strict=True)`，再以 `candidate.relative_to(root)` 验证；拒绝绝对路径、`..`、越根符号链接和任意用户路径。
- DOCX 预览由服务器从允许的段落/标题/表格节点构造并 `html.escape`；在 sandbox iframe 中加载，响应设置 CSP 和 `X-Content-Type-Options: nosniff`。前端不使用 `v-html`。
- 批注锚定的稳定键为 `document_id + file_hash + page_number + geometry + selected_text + selected_text_hash`；不同 hash 的批注查询只作为历史/需重新定位返回。
- OCR 采用应用内单并发 worker（应用生命周期启动/恢复 pending run）和 `asyncio.to_thread`/受控子进程；数据库 run 是事实源。进程重启后，运行中 run 标为可重试失败，而不是声称仍在执行。
- PMC 仅调用允许的官方端点。审计已阅读 PMC OAI-PMH 和版权说明：OAI-PMH 可为可复用文章提供全文 XML；自动获取只允许指定官方服务，主站批量/系统下载禁止；许可逐篇不同，缺失许可必须拒绝。

## 7. 依赖与 Windows 部署决策

| 能力 | 冻结建议 | 依据与部署影响 |
|---|---|---|
| 上传/解析 | 复用 `python-multipart`、`pypdf`、`python-docx`、标准库 `hashlib/pathlib/html`。 | 当前已安装；`pypdf` 的已安装元数据为 BSD-3-Clause，`python-docx` 为 MIT。无须引入 MIME native 库。 |
| PDF 批注 | 阶段 3 才新增并锁定 `pdfjs-dist`；版本在用户确认阶段 3 时按兼容性审计后固定。 | 当前前端依赖中没有 `pdfjs-dist` 或 HTML sanitizer。PDF.js 官方仓库明确其 npm 分发名为 `pdfjs-dist` 且为 Apache-2.0。 |
| Word 预览 | 第一版不引入 Office 在线服务或浏览器 Office 控件；复用可信服务器端抽取并输出转义 HTML。 | 保持本地优先，无需把原文发送第三方。DOC 依赖 LibreOffice/antiword/catdoc，当前均未安装，因此先诚实不支持。 |
| OCR | 推荐 Tesseract CLI（含明确安装路径/版本/`eng` 与可选 `chi_sim` 语言包） + `pypdfium2` 作为 PDF 栅格化候选；以环境变量显式启用。 | 本机缺 Tesseract、pytesseract、PyMuPDF；不把 Codex 自带 Poppler 当产品依赖。Tesseract 为 Apache-2.0；pypdfium2 是 Apache-2.0/BSD-3-Clause，但 Windows wheel 内 PDFium 的全部随附许可证必须在发布物中保留。因而阶段 4 先做安装探测和门控测试。 |
| PMC 全文 | 标准库 XML + 现有 `httpx`；独立官方 OAI-PMH adapter，不引入爬虫。 | OAI-PMH 新 base URL 为 `https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/`；每篇限制、超时、串行限流、重试和许可审计是功能的一部分。 |

参考： [PMC OAI-PMH API](https://pmc.ncbi.nlm.nih.gov/tools/oai/)、[PMC Copyright Notice](https://pmc.ncbi.nlm.nih.gov/about/copyright/)、[PDF.js](https://github.com/mozilla/pdf.js/)、[Tesseract](https://github.com/tesseract-ocr/tesseract)、[pypdfium2 licensing](https://github.com/pypdfium2-team/pypdfium2)。以上仅为工程许可证/服务边界记录，不替代法律意见。

## 8. 测试现状与后续验收矩阵

已存在测试覆盖：Document 状态机/重试/缺源、PDF/DOCX/DOC 解析、知识源符号链接和权限、PaperQA2 索引、LibraryItem 元数据与本地 PDF 关联、Task API、PubMed 解析/超时/限流、无外部网络的安全忽略规则，以及文档管理前端组件。

后续新增测试必须按功能拆分：

| 阶段 | 后端 | 前端 |
|---|---|---|
| 1 | 合法 PDF、伪 MIME、伪扩展名、空/超限/损坏、越界路径、写入失败、临时文件清理、事务回滚。 | 单文件选择、非法文件、上传中、成功刷新、服务端错误、键盘/label。 |
| 2 | id 边界、根目录/符号链接越界、头部、Range、PDF/DOCX/DOC 支持矩阵、无路径泄漏。 | 详情页加载/失败/不可预览、iframe sandbox、回文档库。 |
| 3 | schema 边界、hash 409、软删除、XSS 文本、坐标/页码校验。 | 选区建批注、失败、按页定位、历史 hash 状态；一条 E2E。 |
| 4 | 引擎替身的 queued/running/succeeded/partial/failed/cancelled/retry、页级输出、索引过期。 | 扫描件条件展示、真实状态、OCR 后的摘要/重索引提示。真实引擎测试仅环境变量门控。 |
| 5 | 官方 adapter mock：无 PMCID、许可拒绝、XML/网络/限流/哈希失败、成功后才关联 Document。 | 条件按钮、来源/许可/拒绝/失败/成功跳转。真实网络测试默认关闭。 |

本阶段实际命令和结果：

| 命令 | 真实结果 |
|---|---|
| `F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m alembic current` | `f6a7b8c9d0e1 (head)`。 |
| `... -m alembic heads` | 同一单 head。 |
| `... -m pytest tests/modules/document tests/parsers tests/modules/indexing tests/modules/knowledge_source tests/modules/library tests/modules/task tests/unit/test_pubmed_client.py tests/modules/literature_search/test_pubmed_executor.py -q` | **86 passed, 1 skipped**，27.32 秒；有 1 条 Starlette TestClient 弃用警告。 |
| `frontend: npm run typecheck` | 通过。 |
| `frontend: npm run build` | 通过；Vite 构建完成。 |
| `frontend: npm test` | **失败：35 passed, 1 failed**。`src/router/router.test.ts` 仍期望“工作台 / 示例研究项目”，当前渲染是现有改动后的新文案。另有既有 RouterLink/路由未匹配警告。未改动用户的前端文件。 |
| `... -m ruff check app` | **失败：16 项既有 lint**（含 `PubMedClient.__aenter__`、文档索引的宽泛捕获、其他模块格式/类型规则）。未在阶段 0 做无关修复。 |
| `... -m mypy` | **失败：1 项既有环境/依赖问题**：`app/integrations/scispacy_client.py` 缺 `spacy` stub/实现。 |

## 9. 合并顺序、独立任务与风险登记

### 可以合并的工作

- 阶段 1 的 `document_assets` 与 `temporary_import` 初始化是一个原子上传事务，必须一起交付。
- 阶段 2 的安全文件解析器可被阶段 3 的 PDF.js 文件加载和阶段 5 的受控全文资产复用。
- 阶段 4 完成 OCR 后复用现有 `DocumentService.parse` 和 `DocumentIndexService` 的“索引过期”语义，但重新解析/索引仍是可观察的真实任务。
- 阶段 5 获取成功后复用阶段 1 的资产落盘、哈希和 Document 创建能力；不复用 PubMed 元数据 client 来下载全文。

### 必须拆开的工作

1. 上传与预览：上传安全接受策略、浏览器流式响应和 DOCX HTML 威胁模型不同，必须分别验收。
2. 基础预览与批注：阶段 2 用浏览器原生 PDF 预览，阶段 3 才因文本选区需要引入 PDF.js；不能提前以不完整阅读器冒充批注能力。
3. OCR：需要外部引擎、可恢复 worker、页级审计和独立状态，不能塞入 parse 请求。
4. PMC 全文：版权/许可/官方适配器/审计记录与 PubMed 元数据业务边界不同，必须是独立集成和独立测试。

### 当前阻塞与风险

- **阶段 1 前基线：** 前端全量 Vitest 有 1 个失败；该断言/相关工作区文件需由其当前修改者确认或修复后，再将其作为后续阶段的全量绿色门槛。后端相关回归通过。
- **阶段 4 前环境：** 未安装 OCR 运行时。没有经用户确认的 Tesseract/语言包和 `pypdfium2` Windows wheel 时，OCR 功能只能显示不可用，不能验收成功。
- **阶段 5 前合规：** 必须以每篇官方 OAI-PMH 返回的可复用许可为准；PMCID 或“免费阅读”本身不构成可自动下载/复用授权。
- **现有预览路径：** 当前 Document 物理路径的读取服务没有作为公开安全边界设计；阶段 2 不能直接暴露它。
- **范围控制：** 当前存在与本任务无关的前端未提交修改、lint 和 mypy 基线问题。本阶段未重置、覆盖或修复它们。

## 10. 阶段 0 交付与下一步

本阶段变更文件：

- `docs/implementation-audits/document-asset-loop-audit.md`（本文件）。

未写业务代码、未新增依赖、未执行数据库迁移、未安装 OCR、未访问任何真实 PMC 文章、未获取或生成任何论文全文/OCR 文本。

**设计已冻结，等待用户明确确认后才开始阶段 1：单 PDF 安全上传。**
