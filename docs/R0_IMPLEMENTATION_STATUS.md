# R0 实施状态

## 当前工作包

- 工作包：R0-WP02《脚手架、SQLite 与 Alembic》
- 状态：已完成
- 负责模块：后端基础设施
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

## 已知限制

- 当前业务模块主要为脚手架，完整 RAG、检索、写作和 Agent 能力尚未实现。
- R0-WP01 不启用认证，因此未生成 JWT 密钥；该事项已记录到 Backlog。
- `.codex/` 是未跟踪的本地任务资料，不属于本工作包交付物。
- 工作区包含本工作包新增/修改文件以及实施前已存在的未跟踪 `.codex/`；本任务未创建提交，因此验收所称“干净”按“除预期交付改动外无额外改动”解释。
- 当前 FastAPI/Starlette `TestClient` 会提示未来改用 `httpx2`；现有测试仍通过，暂不在本工作包升级依赖。
- 现有脚手架表名 `literature_searchs` 和 `paper_analysiss` 沿用仓库原定义；本工作包不进行业务模型命名重构。

## 下一任务

以当前阶段后续工作包文档为准；R0-WP02 完成后仅说明下一任务，不提前执行。
