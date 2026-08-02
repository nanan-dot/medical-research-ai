# R0 阶段验收与复现报告

- 阶段：R0 工程基线与 PaperQA 最小问答链路
- 验收日期：2026-08-02
- 分支：`feature/r0-wp01-baseline`
- 结论：通过，可进入 R1 规划；非阻塞限制已列入 `docs/R1_BACKLOG.md`。

## 环境矩阵

| 组件 | 验收版本/配置 | 结果 |
|---|---|---|
| Windows / PowerShell | Windows，本机无 Profile shell | 通过 |
| 应用 Python | 3.12.13 | 通过 |
| PaperQA Python | 3.13.9 | 通过 |
| FastAPI | 0.141.1 | 通过 |
| SQLAlchemy / Alembic | 2.0.51 / 1.18.5 | 通过 |
| PaperQA2 | `paper-qa==2026.3.18` | 通过 |
| Ollama | 0.21.2 | 通过 |
| 本地模型 | `qwen3:4b` | 通过 |
| 本地嵌入 | `nomic-embed-text` | 通过 |
| 云端兼容模型 | `deepseek-v4-flash` | 通过 |

应用与测试的直接版本锁见 `requirements-r0.lock`；PaperQA2 隔离锁见 `experiments/paperqa2_r0/requirements.lock`。R0 锁定直接依赖而非全部传递依赖哈希，完整跨平台锁文件属于 R1。

## 干净环境复现

使用规定 conda Python 创建新的、被 Git 忽略的环境并从锁文件安装：

```powershell
Set-Location H:\AI_project\rag_medicine
$env:PYTHONPATH=''
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m venv data\r0-clean-venv
& data\r0-clean-venv\Scripts\python.exe -m pip install -r requirements-r0.lock
& data\r0-clean-venv\Scripts\python.exe -m pytest
& data\r0-clean-venv\Scripts\python.exe -m mypy
& data\r0-clean-venv\Scripts\ruff.exe check app tests scripts alembic experiments
```

实际结果：安装成功；Python 3.12.13；应用导入成功；默认测试 79 passed、3 skipped；mypy 与 Ruff lint 通过。

## 验收矩阵

| 验收项 | 实际执行与结果 |
|---|---|
| 健康检查 | 干净环境启动 Uvicorn；`GET /api/v1/health` 返回 `status=ok` |
| Swagger | `GET /docs` 返回 HTTP 200 |
| 数据库迁移 | 独立 `data/r0_acceptance.db` 完成 upgrade→downgrade→upgrade，最终 `098a8f062646 (head)` |
| 云端 smoke | `deepseek-v4-flash` 返回 `cloud-llm-ok`，0.843 秒 |
| Ollama smoke | 两次返回 `ollama-local-ok`，3.907/3.637 秒 |
| PaperQA CLI | `qwen3:4b` 成功；建索引 11.465 秒、问答 13.858 秒 |
| 云端 integration | 1 passed（1.18 秒） |
| Ollama integration | 1 passed（7.81 秒） |
| PaperQA2 integration | 1 passed（23.89 秒） |
| 默认回归 | 79 passed、3 skipped |
| 安全与类型 | Git/Key 检查、mypy、Ruff lint、Alembic check 通过 |

## 人工来源核对

- 公开论文 SHA-256：`b6edeac8ee9ebad3faf4672c9334241d0161305e8c626ca5cf9ea47e7d1b5c1e`。
- PDF 共 20 页，文本可提取。
- PaperQA 关键来源：`pages 11-12`。
- 人工打开/直接提取 PDF 第 11 页，确认原文报告 507 个累计首次微血管和大血管事件，其中干预组 233 个（40.5%）、常规护理组 274 个（48.0%）。
- 演示答案与原文数字一致。该核对只验证论文报告内容，不构成医学建议或独立临床结论。

## Git 与范围评审

R0 工作包提交从 `65189fe` 到当前阶段提交保持独立、顺序清晰。`.env`、PDF、数据库、索引、日志和完整运行 JSON 未被跟踪。

审查 `experiments/` 后仅存在 WP05 的 PaperQA2 固定版本实验，它仍是版本决策和回归证据，不属于无关代码，因此未删除。`.codex/` 是用户本地任务资料，保持未跟踪且未修改。

## 已知限制与 R1 准入

- 索引只在客户端进程内复用，不支持跨进程持久化。
- PaperQA 页码通常是文本块范围而非精确单页。
- `qwen3:4b` 可能返回较长思考文本；复杂科研综合准确性有限。
- LiteLLM 没有 `deepseek-v4-flash` 价格映射。
- 全仓仍有 28 个早期脚手架文件不符合 Ruff formatter，但 lint、测试和本轮文件格式均通过。
- Starlette TestClient 有迁移到 `httpx2` 的第三方弃用警告。

R1 准入条件已满足：健康与迁移可复现；本地和云端模型可调用；PaperQA2 有固定版本、稳定适配器、真实问答和来源证据；默认测试无费用；安全边界与失败模式有自动化覆盖；剩余事项均有 Backlog 且不阻塞 R0 演示。
