# R0 实施状态

## 当前工作包

- 工作包：R0-WP01《范围、环境和 Git 基线》
- 状态：已完成
- 负责模块：工程基础与项目治理
- 开发分支：`feature/r0-wp01-baseline`

## 已完成

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

## 已知限制

- 当前业务模块主要为脚手架，完整 RAG、检索、写作和 Agent 能力尚未实现。
- R0-WP01 不启用认证，因此未生成 JWT 密钥；该事项已记录到 Backlog。
- `.codex/` 是未跟踪的本地任务资料，不属于本工作包交付物。
- 工作区包含本工作包新增/修改文件以及实施前已存在的未跟踪 `.codex/`；本任务未创建提交，因此验收所称“干净”按“除预期交付改动外无额外改动”解释。

## 下一任务

以当前阶段后续工作包文档为准；R0-WP01 完成后仅说明下一任务，不提前执行。
