# R0 实施状态

## 当前工作包

- 工作包：R0-WP07《最小问答演示链路》
- 状态：已完成
- 负责模块：R0 最小问答演示
- 开发分支：`feature/r0-wp01-baseline`

## 已完成

### R0-WP01

- 已审查仓库结构、Git 状态、`pyproject.toml`、`.env.example` 和 `.gitignore`。
- 已确认仓库没有既有 `README.md` 和 R0 状态文档。
- 已确认 FastAPI/SQLAlchemy/Alembic 分层脚手架存在。
- 已确认 Conda 环境解释器存在且 Python 为 3.12.13。
- 已确认 pip、项目基础依赖和 `app.main` 可导入。
- 已创建 R0 范围和 Backlog 文档。
- 已从 `.env.example` 复制 `.env`，未写入真实密钥。
- 已确认 `data/` 目录存在。
- 已补充本地 PDF 忽略规则。
- 已创建 `feature/r0-wp01-baseline` 分支。

### R0-WP02

- 已为 `GET /api/v1/health` 建立无数据库依赖的类型化健康响应。
- 已通过 Uvicorn 实际启动验证 FastAPI lifespan、健康接口和 Swagger。
- 已集中注册 11 个 SQLAlchemy Model，Alembic 可发现完整元数据。
- 已生成并人工审查首次迁移 `098a8f062646_initial_schema.py`。
- 已执行首次 upgrade、downgrade 到 base、再次 upgrade 到 head。
- 已生成本地 `data/app.db`，其中包含 Alembic 版本表和 11 张业务表。
- 已增加健康接口、应用生命周期、Swagger、模型注册、SQLite 文件和事务回滚测试。
- 已将 Ruff 加入开发依赖并补充启动、迁移和检查说明。

### R0-WP03

- 已实现基于异步 `httpx` 的 OpenAI 兼容非流式 `LLMClient.chat`。
- 已建立 `ChatMessage`、`LLMConfig` 和 `LLMResponse` 数据结构。
- 已通过配置注入供应商、模型、API Base、API Key 和超时，不硬编码密钥。
- 已统一转换配置、认证、模型不存在、限流、超时、连接、供应商和响应结构异常。
- 已实现固定消息云端 Smoke Test 脚本，并记录响应文本和请求耗时。
- 已增加无费用 Mock 测试及默认跳过的显式 opt-in 云端集成测试。
- 已验证日志和安全异常不会包含 API Key、消息正文或供应商错误正文。
- 已补充 OpenAI 和 OpenRouter 的本地配置与手工验证说明。

### R0-WP04

- 已确认 Ollama 0.21.2 安装并运行于本机回环地址。
- 已复用统一 `LLMClient.chat`，通过组合方式实现 Ollama 本地适配器。
- 已配置现有本地模型 `qwen3:4b`，无需重复下载约 2.50 GB 模型文件。
- 已实现服务版本、已下载模型和运行资源检查。
- 已限制 Ollama 地址只能使用本地 HTTP 回环地址，并禁用系统代理继承。
- 已实现服务不可达、端口非 Ollama、模型缺失、首次加载超时、空响应和资源不足异常。
- 已增加连续两次调用和资源记录脚本、Mock 测试及显式本地集成测试。
- 已验证本地失败不会调用 OpenAI、OpenRouter 或其他云端供应商。

### R0-WP05

- 已在 `experiments/paperqa2_r0` 建立独立实验，不接入业务 API、数据库或现有 RAG 层。
- 已固定并真实运行 `paper-qa==2026.3.18`，使用本地 `qwen3:4b` 与 `nomic-embed-text`，无云端回退。
- 已索引一篇公开、非扫描、20 页的 PLOS Medicine PDF，共生成 49 个文本块。
- 已对事实问题返回非空答案：6.5 年累计 507 个首次微血管和大血管事件，其中干预组 233 个、常规护理组 274 个。
- 已保存去敏运行 JSON，包含论文标题、来源、证据摘录、PaperQA 页范围及人工核对页。
- 已验证可信本地索引复用，并以 PaperQA 版本和 PDF SHA-256 防止不匹配索引被加载。
- 已记录用户提供的 `paper-qa-main` 源码快照作为 API 参考；因缺少 SCM 版本元数据，不作为固定运行版本。

### R0-WP06

- 已实现 `PaperQA2Client.index_documents` 和 `PaperQA2Client.ask` 异步接口。
- 已定义稳定的 `PaperDocument`、`PaperQAIndex`、`PaperSource` 和 `PaperQAAnswer`，外部 PaperQA2 对象不会泄漏到业务层。
- 已将同步耗时边界放入工作线程，避免阻塞 FastAPI 事件循环。
- 已按文件路径和 SHA-256 生成稳定索引标识，并定义同一客户端实例内的重复索引复用规则。
- 已转换论文标题、引用、证据、分数和页范围；PaperQA2 未提供页码时保持 `None`。
- 已实现固定版本缺失/不匹配、配置错误、索引不存在/损坏、响应字段变化和外部调用错误的统一异常。
- 已限制本地 Ollama 回环地址、禁用文献元数据联网和云端模型回退。

### R0-WP07

- 已实现 `scripts.r0_paperqa_demo` 命令行入口，接收 PDF、问题、provider、模型、Base URL、输出路径和 rebuild 标记。
- 已通过 WP06 适配器完成索引、问答、回答与来源打印、统一 JSON 保存和分阶段耗时记录。
- 已为 OpenAI、OpenRouter 和 Ollama 模型路由保持同一 `DemoResult`/`PaperQAAnswer` 输出结构；API Key 只从 `.env` 读取。
- 已定义退出码：外部调用失败为 1，输入/配置失败为 2，输出不可写为 3。
- 已处理 Windows 空格路径和 GBK 控制台 Unicode 转义，同时保持 JSON 为完整 UTF-8。

## 测试结果

- `env PYTHONPATH="" ...python.exe --version`：通过，Python 3.12.13。
- 基础依赖与 `app.main` 导入：通过。
- `python -m pytest`：通过，14 passed（0.49s）。
- `python -m alembic check`：通过，未检测到新的升级操作。
- `.env.example` 与 `.env` SHA-256 比对：一致。
- `git check-ignore`：通过，已覆盖 `.env`、`data/`、测试 PDF、数据库、索引、上传和临时目录。
- `git ls-files --error-unmatch .env`：按预期失败，证明 `.env` 未被跟踪。
- `git ls-files '*.pdf'`：无输出，仓库没有已跟踪 PDF。
- `git diff --check`：通过。
- 当前分支确认：`feature/r0-wp01-baseline`。

### R0-WP02 验收

- Uvicorn 启动与正常关闭：通过。
- `GET /api/v1/health`：HTTP 200，返回 `status=ok`。
- `GET /docs`：HTTP 200，Swagger UI 内容存在。
- SQLAlchemy 元数据：注册 11 张业务表。
- Alembic upgrade：通过，升级至 `098a8f062646 (head)`。
- Alembic downgrade：通过，回退至 base。
- Alembic 再次 upgrade：通过，恢复至 `098a8f062646 (head)`。
- `alembic check`：通过，未检测到新的升级操作。
- SQLite：`data/app.db` 已生成，大小 57344 字节；版本表值为 `098a8f062646`。
- `ruff check app tests alembic`：通过。
- `python -m pytest`：19 passed（0.75s），1 条第三方弃用警告。

### R0-WP03 验收

- `LLMClient.chat` 成功 Mock：返回非空文本、供应商、模型和耗时。
- 401/403 认证错误：转换为 `llm_authentication_error`。
- 404 模型或端点错误：转换为 `llm_model_not_found`。
- 429 限流：转换为 `llm_rate_limit_error`。
- 请求超时：转换为 `llm_timeout_error`。
- API Base/代理连接失败：转换为 `llm_connection_error`。
- 返回结构变化或空文本：转换为 `llm_response_format_error`。
- 日志和异常密钥脱敏：通过。
- 缺少本地密钥时运行手工脚本：安全失败，退出码 1，错误码为 `llm_configuration_error`。
- `ruff format --check`（本轮 9 个 Python 文件）：通过。
- `ruff check app tests scripts alembic`：通过。
- `python -m pytest`：35 passed、1 skipped（显式 opt-in 集成测试默认跳过）、1 条第三方弃用警告。
- `alembic check`：通过，未检测到新的升级操作。
- 真实云端 Smoke Test：通过；`deepseek-v4-flash` 返回 `cloud-llm-ok`，耗时 0.994 秒。

### R0-WP04 验收

- Ollama 版本：0.21.2。
- 本地模型：`qwen3:4b`，模型文件 2497293931 字节。
- 首次真实调用：通过，返回 `ollama-local-ok`，耗时 9.102 秒。
- 第二次真实调用：通过，返回 `ollama-local-ok`，耗时 0.556 秒。
- 运行模型资源：加载大小 3523425408 字节，Ollama 报告 VRAM 3523425408 字节。
- 服务关闭等价检查：通过；不可达回环端口返回 `ollama_service_unavailable`，退出码 1。
- 真实模型不存在检查：通过；返回 `ollama_model_not_found`，退出码 1。
- 真实本地集成测试：1 passed（2.15s）。
- Ollama Mock 测试：10 项通过，覆盖服务、模型、空响应、超时、资源和无云端回退。

### R0-WP05 验收

- 首次真实运行：通过；1 篇论文、49 个文本块、10 个检索来源，建索引 3.129 秒，问答 16.186 秒。
- 第二次真实运行：通过；复用同一索引，加载 0.002 秒，问答 15.742 秒。
- 两轮均返回非空答案，并包含可在 PDF 第 11 页人工核对的 `507 / 233 / 274`。
- 来源能力：论文标题存在，来源数为 10，PaperQA 文本块页范围存在（关键证据为 `pages 11-12`）。
- 独立实验测试：4 passed，覆盖错误 PDF 路径、索引保存/复用、版本与文件哈希失配、目录越界及结果 JSON 保存。
- Ruff：实验代码和测试通过。

### R0-WP06 验收

- PaperQA2 Adapter 单元测试：12 passed，覆盖返回转换、缺失页码、空来源、字段变化、异常脱敏、固定版本、索引损坏、重复索引和线程隔离。
- 真实 PDF 集成测试：1 passed；实际完成索引、重复索引复用、事实问答、来源转换和统一 JSON 输出。
- 真实答案包含可由原文核对的 `507 / 233 / 274`；关键来源页范围为 `11-12`。

### R0-WP07 验收

- CLI/适配器相关 Mock 测试：20 passed。
- 本地 Ollama 完整 CLI：成功；建索引 10.554 秒、问答 14.316 秒、10 个真实来源。
- OpenAI 兼容云端完整 CLI：`deepseek-v4-flash` 成功；建索引 8.705 秒、问答 5.858 秒、10 个真实来源。
- 云端与本地 JSON 顶层字段及 `PaperQAAnswer` 字段一致，答案均包含 `507 / 233 / 274`。
- 错误 PDF 路径实际返回退出码 2；两份完整 JSON 均已保存到被 Git 忽略的 `data/r0_demo/`。

## 已知限制

- 当前业务模块主要为脚手架，完整 RAG、检索、写作和 Agent 能力尚未实现。
- R0-WP01 不启用认证，因此未生成 JWT 密钥；该事项已记录到 Backlog。
- `.codex/` 是未跟踪的本地任务资料，不属于本工作包交付物。
- `.codex/` 仍为未跟踪任务资料，不属于工作包交付物。
- 当前 FastAPI/Starlette `TestClient` 会提示未来改用 `httpx2`；现有测试仍通过，暂不在本工作包升级依赖。
- 现有脚手架表名 `literature_searchs` 和 `paper_analysiss` 沿用仓库原定义；本工作包不进行业务模型命名重构。
- 本地 `.env` 已配置用户提供的模型名并完成一次真实调用；密钥仍仅保存在被 Git 忽略的 `.env` 中。
- 全仓库额外格式检查发现 29 个既有脚手架文件不符合 Ruff formatter；为避免无关重构，本工作包仅格式化自身 9 个 Python 文件，Ruff lint 全仓通过。
- `qwen3:4b` 当前完全加载到 Ollama 报告的 VRAM；不同硬件、上下文长度和并发量会改变资源占用。
- 为避免干扰用户正在运行的服务，服务关闭验证使用不可达回环端口等价执行，没有终止 Ollama 进程。
- PaperQA 当前返回文本块页范围，而非始终提供单页精确定位；本次关键来源为 `pages 11-12`，人工核对位置为 PDF 第 11 页。
- `qwen3:4b` 的原始回答包含较长思考文本；样本保留实际最终答案和截断标记，运行时完整去敏 JSON 位于被忽略的 `data/paperqa2_r0/`。
- 实验索引使用 pickle，仅允许加载本实验数据目录内、版本和 PDF 哈希一致的本机生成文件；不接受外部索引。
- WP06 适配器索引是客户端实例内的进程状态，进程重启后索引引用失效并需要重新索引；持久化索引不在本工作包范围。
- 来源证据最多返回 1000 个字符，避免适配器响应携带完整文档文本；调用方仍需对未发表或敏感材料实施访问控制。
- 一次性演示 CLI 每次启动新进程，因此当前会重新建立 WP06 的进程内索引；`--rebuild` 可强制同一客户端实例重建，但跨进程持久化仍不在 R0-WP07 范围。
- LiteLLM 尚无 `deepseek-v4-flash` 的价格映射，云端回答成功但无法自动估算成本。

## 下一任务

下一任务为 R0-WP08；必须先读取任务文档，不提前执行。
