# 医学科研智能助手平台

基于 FastAPI、SQLAlchemy 与 Alembic 的医学科研辅助平台脚手架。当前仓库处于 R0 工程基线阶段；业务模块仅提供分层骨架，不代表完整知识库、检索或 Agent 能力已经实现。

## 环境要求

- Conda 环境：`med-research-ai`
- Python：3.12
- 工作目录：`H:\AI_project\rag_medicine`

本机全局 `PYTHONPATH` 指向其他虚拟环境。运行本项目时必须清空它，避免从错误环境加载包。

### Git Bash

```bash
cd /h/AI_project/rag_medicine
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe --version
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m uvicorn app.main:app --reload
```

### PowerShell

PowerShell 中用进程级环境变量达到同样效果：

```powershell
Set-Location H:\AI_project\rag_medicine
$env:PYTHONPATH = ""
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe --version
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m pytest
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m uvicorn app.main:app --reload
```

## 本地配置

首次使用时从模板复制配置，不要从零创建，也不要提交真实密钥：

```powershell
Copy-Item .env.example .env
```

`.env`、`data/`、数据库、索引和 PDF 均由 Git 忽略。R0 的实验数据统一放在 `data/`；不得提交未发表论文或敏感材料。

## 验证基线

```bash
git branch --show-current
git check-ignore .env data/test.pdf data/app.db test.pdf
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m alembic check
git status --short --branch
```

预期分支为 `feature/r0-wp01-baseline`。`git check-ignore` 应输出所有测试路径；测试和 Alembic 检查应成功。

## FastAPI、SQLite 与 Alembic

启动服务：

```bash
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m uvicorn app.main:app --reload
```

启动后访问：

- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- Swagger：`http://127.0.0.1:8000/docs`

首次迁移和回滚验证：

```bash
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m alembic upgrade head
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m alembic current
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m alembic history
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m alembic downgrade base
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m alembic upgrade head
ruff check app tests alembic
```

## Git 约定

- 功能开发从专用分支进行，不直接在 `master` 开发。
- 提交信息使用英文 Conventional Commits，例如：`chore(r0): establish scope environment and git baseline`。
- 每次提交前检查 `git status`，确保 `.env`、数据、数据库、索引、PDF 和密钥未进入暂存区。

R0 的详细边界与后续事项见 `docs/R0_SCOPE.md` 和 `docs/R0_BACKLOG.md`。
