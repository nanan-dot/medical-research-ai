# 医学科研智能助手平台

基于 FastAPI、SQLAlchemy、Alembic 与 Vue 3 的医学科研辅助平台。R0 工程基线已验收，R1 当前完成知识源登记与授权目录管理；尚不代表完整知识库、检索或 Agent 能力已经实现。

## 环境要求

- Conda 环境：`med-research-ai`
- Python：3.12
- 工作目录：`H:\AI_project\rag_medicine`

R0 验收版本可使用 `requirements-r0.lock` 安装；PaperQA2 使用独立的 `experiments/paperqa2_r0/requirements.lock`。阶段验收证据见 `docs/R0_ACCEPTANCE.md`，R1 候选事项见 `docs/R1_BACKLOG.md`。

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

## 云端模型最小调用

统一客户端使用 OpenAI 兼容的非流式 `POST /chat/completions` 接口。先在本地 `.env` 中选择并配置一个供应商；真实密钥不得写入 `.env.example` 或提交到 Git。

OpenAI 示例：

```dotenv
DEFAULT_MODEL_PROVIDER=openai
OPENAI_API_KEY=<your-api-key>
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=<your-model-name>
LLM_TIMEOUT_SECONDS=30
```

OpenRouter 示例：

```dotenv
DEFAULT_MODEL_PROVIDER=openrouter
OPENROUTER_API_KEY=<your-api-key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=<your-model-name>
LLM_TIMEOUT_SECONDS=30
```

确认账户权限和可能产生的费用后，执行一次手工 Smoke Test：

```bash
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m scripts.r0_test_cloud_llm
```

真实集成测试默认跳过。只有显式授权一次真实请求时才设置开关：

```bash
RUN_CLOUD_LLM_TEST=1 env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest tests/integrations/test_cloud_llm.py
```

错误模型名应返回 `llm_model_not_found`；无效密钥应返回 `llm_authentication_error`。客户端不会在日志或异常信息中记录密钥、消息正文或供应商响应正文。

## Ollama 本地模型最小调用

本地适配器复用统一 `LLMClient.chat`，但只允许 `localhost` 或回环地址，不配置也不会触发云端回退。当前验证模型：`qwen3:4b`。

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
OLLAMA_TIMEOUT_SECONDS=120
```

检查服务和已下载模型：

```powershell
ollama --version
ollama list
```

如果模型尚未安装：

```powershell
ollama pull qwen3:4b
```

执行两次连续本地调用并比较首次、再次耗时与资源占用：

```bash
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m scripts.r0_test_ollama
```

显式运行真实本地集成测试：

```bash
RUN_OLLAMA_TEST=1 env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest tests/integrations/test_ollama.py
```

若服务关闭，客户端返回 `ollama_service_unavailable`；若模型不存在，返回 `ollama_model_not_found`。本地失败不会切换至 OpenAI、OpenRouter 或其他云端供应商。

## PaperQA2 独立实验

R0-WP05 在业务系统外验证固定版本 `paper-qa==2026.3.18`。实验使用本地 Ollama `qwen3:4b` 和 `nomic-embed-text`，处理公开 PLOS Medicine PDF，并验证来源、页范围和本地索引复用。安装、运行、人工核对和已知限制见 `experiments/paperqa2_r0/README.md`。

## PaperQA2 适配器

R0-WP06 通过 `app.integrations.paperqa2` 隔离 PaperQA2。业务代码只接收 `PaperQAIndex`、`PaperQAAnswer` 和 `PaperSource`，不会接触 `Docs`、`PQASession` 或其他外部类型。同步耗时边界通过工作线程运行，避免阻塞 FastAPI 事件循环。

```dotenv
PAPERQA_VERSION=2026.3.18
PAPERQA_EMBEDDING_MODEL=nomic-embed-text
PAPERQA_TIMEOUT_SECONDS=300
```

最小调用：

```python
from app.integrations.paperqa2 import PaperDocument, create_paperqa2_client

client = create_paperqa2_client()
index = await client.index_documents([PaperDocument(path="data/paper.pdf")])
answer = await client.ask(index, "What does the paper report?")
print(answer.model_dump_json(indent=2))
```

适配器索引当前为进程内状态：相同文件路径和 SHA-256 在同一客户端实例中返回同一索引标识，并设置 `reused=true`；进程重启后需要重新索引。真实 PDF 集成测试只使用本地 Ollama，须在安装固定 PaperQA2 的隔离环境中显式运行：

```powershell
$env:PYTHONPATH=''
$env:RUN_PAPERQA2_TEST='1'
$env:OLLAMA_MODEL='qwen3:4b'
& C:\Users\ADMIN\.paperqa-codex-venv\Scripts\python.exe -m pytest tests\integrations\test_paperqa2_adapter_integration.py -q -s
```

## R0 最小问答演示

端到端命令行入口为 `python -m scripts.r0_paperqa_demo`，支持 PDF 路径、问题、`ollama/openai/openrouter` 模型配置、`--rebuild`、统一 JSON 输出和分阶段耗时。已使用同一公开 PDF 实际验证本地 `qwen3:4b` 与 OpenAI 兼容的 `deepseek-v4-flash`，两者输出结构一致。完整命令、实际耗时、退出码和限制见 `docs/R0_DEMO.md`。

## R0 安全与回归

默认 pytest 不调用真实云端或本地模型；integration 测试必须显式启用。错误码、日志脱敏、Git 敏感文件规则和 Windows 权限等价测试见 `docs/R0_SECURITY_CHECKLIST.md`，完整场景矩阵与回归命令见 `docs/R0_TEST_REPORT.md`。

## R0 阶段状态

R0 已于 2026-08-02 完成阶段验收。开发者现场演示、干净环境安装、健康检查、迁移回滚、云端与本地模型、PaperQA2 问答、人工来源核对和显式 integration 均已实际通过。详情以 `docs/R0_ACCEPTANCE.md` 为准。

## R1 知识源管理

知识源 API 支持登记本地文件夹、Obsidian Vault 和临时导入目录：

- `GET/POST /api/v1/knowledge-sources`
- `GET/PATCH/DELETE /api/v1/knowledge-sources/{id}`

服务端会解析符号链接、规范化 Windows 路径、检查目录存在性与可读性，并拒绝重复目录。删除接口只移除数据库记录，不扫描或删除授权目录中的原始文件。目录移动或网络盘暂时不可用时，已登记来源会显示为 `unavailable`。

最小 Vue 3 前端位于 `frontend/`：

```powershell
Set-Location frontend
npm install
npm run typecheck
npm test
npm run build
npm run dev
```

当前 R1 工作包状态和验收记录见 `docs/R1_IMPLEMENTATION_STATUS.md`。

### 增量同步

对已启用知识源执行同步：

```text
POST /api/v1/knowledge-sources/{id}/sync
GET  /api/v1/knowledge-sources/{id}/sync-status
```

扫描支持 `.pdf`、`.md`、`.docx`、`.txt`，自动忽略 `.obsidian`、`.git`、`.trash`。文件使用流式 SHA-256；摘要持久化新增、修改、删除、跳过和失败数量。内容变化将 Document 标记为 `outdated`，后续索引工作包可据此重建；本工作包不读取文件正文、不创建向量索引，也不修改原文件。

### 文档状态与任务

文档 API 提供解析/索引双状态、失败信息、过滤分页及安全重试：

```text
GET    /api/v1/documents
GET    /api/v1/documents/{id}
POST   /api/v1/documents/{id}/retry-parse
POST   /api/v1/documents/{id}/retry-index
DELETE /api/v1/documents/{id}/index
```

解析状态为 `pending/parsing/succeeded/failed`，索引状态为 `pending/indexing/succeeded/failed/outdated`。重试只把符合前置条件的失败任务重新置为 `pending`，不伪造处理成功；运行超过 30 分钟且没有完成报告的任务会在查询时标记为 `failed`。源文件被外部删除时，解析不会继续显示成功。

### PDF 与 Markdown 解析

```text
POST /api/v1/documents/{id}/parse
GET  /api/v1/documents/{id}/content-summary
```

PDF 解析逐页保存 1-based 页码，基础移除跨页重复页眉页脚并识别低文本量扫描版；扫描版不会自动 OCR。Markdown 使用严格 UTF-8，读取 YAML front matter、标题层级和正文。解析结果保存在本地数据库，摘要接口仅返回标题、页码、章节、YAML 元数据、扫描提示和字符数。
