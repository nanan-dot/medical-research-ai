# R0 异常、安全与回归测试报告

- 工作包：R0-WP08
- 日期：2026-08-02
- 默认策略：所有云端和本地真实集成测试默认跳过，普通测试仅使用 Mock 或本地文件系统。

## 场景覆盖

| 场景 | 覆盖证据 | 结果 |
|---|---|---|
| PDF 不存在 | `test_r0_demo`, 实际 CLI 错误路径 | 退出码 2 |
| 非 PDF / 伪 PDF | `test_r0_regression` | 明确输入错误 |
| API Key 错误 | LLM 401/403 Mock | `llm_authentication_error`，Key 不泄漏 |
| 模型名错误 | LLM 404 Mock | `llm_model_not_found` |
| 云端超时 | `httpx.ReadTimeout` Mock | `llm_timeout_error` |
| Ollama 未启动 | 连接拒绝 Mock；WP04 不可达回环实测 | `ollama_service_unavailable` |
| Ollama 模型不存在 | tags/404 Mock；WP04 实测 | `ollama_model_not_found` |
| PaperQA2 失败 | 后端异常 Mock | `paperqa2_operation_error`，原文脱敏 |
| 索引/输出目录不可写 | Windows 文件父目录等价测试 | 明确文件系统错误；CLI 为退出码 3 |
| 来源无页码 | PaperQA2 Context Mock | `page_start/page_end=None` |
| 回答为空 | PaperQA2 与 CLI Mock | 明确响应错误 |
| 测试数据进入 Git | `git check-ignore`、`git ls-files` | 无敏感运行文件被跟踪 |
| 密钥进入日志/异常 | caplog、真实 Key tracked-file 扫描 | 未发现泄漏 |

## 回归命令

```powershell
$env:PYTHONPATH=''
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m pytest
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m mypy
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe -m alembic check
& F:\software\programme\Anaconda\Scripts\ruff.exe check app tests scripts alembic experiments
```

显式本地 PaperQA2 集成测试：

```powershell
$env:RUN_PAPERQA2_TEST='1'
$env:OLLAMA_MODEL='qwen3:4b'
& C:\Users\ADMIN\.paperqa-codex-venv\Scripts\python.exe -m pytest tests\integrations\test_paperqa2_adapter_integration.py -q
```

默认回归结果和显式集成测试的最终次数记录在 `docs/R0_IMPLEMENTATION_STATUS.md`。Starlette 的 `httpx2` 弃用警告来自现有第三方测试客户端，不影响当前通过结果。

## WP08 实际结果

- 默认 pytest：79 passed、3 skipped、1 条既有第三方弃用警告。
- 显式本地 PaperQA2 integration：1 passed（26.41 秒）。
- Ruff lint：通过。
- mypy：16 个 CLI/integrations 源文件无问题。
- Alembic check：无新升级操作。
- 全仓 Ruff format：28 个既有脚手架文件仍需格式化；本工作包文件单独检查通过，未扩大为无关格式重写。
