# R0 PaperQA 最小问答演示

该命令行演示接收一篇文本型 PDF、事实问题和显式模型配置，通过 WP06 适配器完成索引与问答，打印回答和来源，并原子写入统一 JSON。它不是正式产品 API。

## 前置条件

- 在隔离 Python 3.13 环境中安装 `paper-qa==2026.3.18`。
- Ollama 链路需要 `qwen3:4b` 和 `nomic-embed-text`。
- 云端链路从被 Git 忽略的 `.env` 读取 API Key；命令行不接受 Key，避免出现在 shell 历史中。
- 所有 Python 命令先清空本机污染的 `PYTHONPATH`。

## 本地 Ollama

```powershell
$env:PYTHONPATH=''
& C:\Users\ADMIN\.paperqa-codex-venv\Scripts\python.exe -m scripts.r0_paperqa_demo `
  --pdf 'H:\AI_project\rag_medicine\data\paperqa2_r0\plos-medicine-carrs-followup.pdf' `
  --question 'How many cumulative first microvascular and macrovascular events occurred during 6.5 years of observation, and how many were in the intervention and usual-care groups?' `
  --provider ollama `
  --model 'qwen3:4b' `
  --base-url 'http://127.0.0.1:11434' `
  --output 'H:\AI_project\rag_medicine\data\r0_demo\ollama-result.json'
```

实际结果：成功；建索引 10.554 秒，问答 14.316 秒，返回 10 个来源。

## OpenAI 兼容云端

下面的命令从 `.env` 读取 `OPENAI_BASE_URL`、`OPENAI_MODEL` 和 `OPENAI_API_KEY`：

```powershell
$env:PYTHONPATH=''
& C:\Users\ADMIN\.paperqa-codex-venv\Scripts\python.exe -m scripts.r0_paperqa_demo `
  --pdf 'H:\AI_project\rag_medicine\data\paperqa2_r0\plos-medicine-carrs-followup.pdf' `
  --question 'How many cumulative first microvascular and macrovascular events occurred during 6.5 years of observation, and how many were in the intervention and usual-care groups?' `
  --provider openai `
  --output 'H:\AI_project\rag_medicine\data\r0_demo\cloud-result.json'
```

实际结果：`deepseek-v4-flash` 成功；建索引 8.705 秒，问答 5.858 秒，返回 10 个来源。LiteLLM 无该模型价格映射，因此仅成本估算不可用，不影响回答。

两条链路都输出 `DemoResult`：顶层字段和 `PaperQAAnswer` 字段完全一致。两者均回答 507 个事件，其中干预组 233 个、常规护理组 274 个；关键证据来自 PDF/PaperQA 页范围 `11-12`。去敏结构样本见 `docs/examples/r0_demo_result.sample.json`；完整运行结果保存在被忽略的 `data/r0_demo/`。

## 错误与索引规则

- argparse 缺少必填参数：退出码 2。
- PDF 不存在、扩展名错误、问题为空或模型缺失：退出码 2。
- 输出目录不可写：退出码 3。
- PaperQA2 或模型调用失败：退出码 1。
- `--rebuild` 强制适配器丢弃同一客户端实例中的匹配索引并重建；一次性 CLI 的新进程本身也会重建。相同客户端实例内重复文档默认复用索引；若复用耗时超过 `--max-reuse-seconds`，命令失败而不掩盖性能回归。

Windows 路径建议使用 PowerShell 单引号。终端不支持某些 Unicode 字符时，人类可读输出使用反斜杠转义，UTF-8 JSON 保留原字符。
