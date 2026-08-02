# R0 安全检查清单

## 外部边界

- 云端 LLM：API Key 仅从 `.env` 进入 `SecretStr`；日志只记录 provider、model 和耗时，不记录请求正文、Authorization 或供应商错误正文。
- Ollama：只允许 HTTP 回环地址；本地失败不会回退到云端。
- PaperQA2：固定 `2026.3.18`，外部对象不进入业务层，异常转换为稳定错误码；来源摘录上限 1000 字符。
- CLI：API Key 不作为命令行参数；JSON 使用原子替换；输入错误、外部错误和输出错误使用不同退出码。

## 文件与 Git

自动化测试逐项确认以下路径被忽略：`.env`、`.env.local`、`data/`、`uploads/`、`logs/`、PDF 和索引。另通过 `git ls-files` 确认没有跟踪环境文件、PDF、数据库、日志或运行数据。

本机存在云端 Key 时，安全测试会在内存中读取 Key，并逐个扫描 Git 已跟踪文件；测试不会打印 Key。提交前还应运行：

```powershell
git status --short
git ls-files '*.pdf' '*.db' '*.sqlite3' '*.log' '.env' '.env.local'
```

## 日志脱敏规则

允许：错误码、HTTP 状态码、provider、model、耗时、通用操作说明。

禁止：API Key、Authorization Header、完整用户问题、完整供应商响应、未发表论文全文、外部异常原文。外部异常通过 `raise ... from error` 保留调试因果，但对外 `.message` 必须为适配器生成的安全文本。

## 错误码清单

| 边界 | 主要错误码 |
|---|---|
| 云端 LLM | `llm_authentication_error`, `llm_model_not_found`, `llm_timeout_error`, `llm_connection_error`, `llm_provider_error`, `llm_response_format_error` |
| Ollama | `ollama_configuration_error`, `ollama_service_unavailable`, `ollama_model_not_found`, `ollama_timeout`, `ollama_resource_error`, `ollama_response_error` |
| PaperQA2 | `paperqa2_configuration_error`, `paperqa2_not_installed`, `paperqa2_version_error`, `paperqa2_document_error`, `paperqa2_index_not_found`, `paperqa2_index_corrupt`, `paperqa2_response_error`, `paperqa2_operation_error` |
| 演示 CLI | 退出码 1（外部调用）、2（输入/配置）、3（输出不可写） |

## Windows 权限说明

Windows ACL、管理员权限和 FAT/NTFS 行为会使 `chmod` 不可写测试不稳定。回归测试使用“普通文件充当父目录”作为确定性的不可写/不可创建等价场景。WP06 当前索引为进程内对象，不写 `PAPERQA_INDEX_DIR`；因此“持久化索引目录不可写”不适用，测试覆盖 CLI 输出目录和未来索引目录创建所依赖的同一文件系统失败类型。
