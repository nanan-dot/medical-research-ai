# R0 实施状态

## 当前工作包

- 工作包：R0-WP03《云端模型最小调用》
- 状态：已完成
- 负责模块：统一云端模型客户端
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

## 已知限制

- 当前业务模块主要为脚手架，完整 RAG、检索、写作和 Agent 能力尚未实现。
- R0-WP01 不启用认证，因此未生成 JWT 密钥；该事项已记录到 Backlog。
- `.codex/` 是未跟踪的本地任务资料，不属于本工作包交付物。
- `.codex/` 仍为未跟踪任务资料，不属于工作包交付物。
- 当前 FastAPI/Starlette `TestClient` 会提示未来改用 `httpx2`；现有测试仍通过，暂不在本工作包升级依赖。
- 现有脚手架表名 `literature_searchs` 和 `paper_analysiss` 沿用仓库原定义；本工作包不进行业务模型命名重构。
- 本地 `.env` 已配置用户提供的模型名并完成一次真实调用；密钥仍仅保存在被 Git 忽略的 `.env` 中。
- 全仓库额外格式检查发现 29 个既有脚手架文件不符合 Ruff formatter；为避免无关重构，本工作包仅格式化自身 9 个 Python 文件，Ruff lint 全仓通过。

## 下一任务

以当前阶段后续工作包文档为准；R0-WP03 完成后仅说明下一任务，不提前执行。
