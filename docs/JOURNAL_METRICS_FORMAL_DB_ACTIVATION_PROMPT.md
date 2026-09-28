# 执行提示词：正式数据库启用期刊指标后端

> 本任务只负责安全启用已通过验收的后端数据库结构并执行上线冒烟检查。不得修改前端，不得导入虚构或来源不明的期刊指标数据。

## 目标

在 `D:\AI_project\rag_medicine` 中，将正式 `data/app.db` 从当前迁移安全升级到仓库最新 Alembic head，并证明升级后的数据库完整、接口可加载、旧业务数据仍可读取。所有结论必须来自真实命令输出。

## 开始前

完整阅读：

- `AGENTS.md`
- `docs/CODE_STANDARDS.md`
- `docs/BACKEND_JOURNAL_METRICS_EXECUTION_PROMPT.md`
- `docs/BACKEND_JOURNAL_METRICS.md`
- 新旧两份期刊指标Alembic迁移。

执行：

```powershell
Set-Location D:\AI_project\rag_medicine
$env:PYTHONPATH = ""
$python = "F:\software\programme\Anaconda\envs\med-research-ai\python.exe"
git status --short
& $python -m alembic heads
& $python -m alembic current
```

保护所有现有未提交修改，不清理、不重置、不提交、不修改 `frontend/`。

## 安全门禁

升级前必须满足：

1. `data/app.db`真实存在。
2. 当前Alembic版本能够被读取，且存在一条无分叉路径到唯一head。
3. 检查是否有本仓库后端、测试、调度器或其他Python进程正在使用正式库。只读检查进程命令行；不得终止无法明确归属于本仓库的进程。
4. 如果明确存在本仓库写入进程，先正常停止；无法安全停止时立即报告阻塞，不执行升级。
5. 使用SQLite自身backup API生成一致性备份，禁止在可能存在WAL状态时只复制主数据库文件。
6. 备份前后分别运行 `PRAGMA quick_check`，结果必须为 `ok`。

## 备份要求

备份目录：

```text
data/backups/
```

文件名：

```text
app-before-journal-metrics-YYYYMMDD-HHMMSS.db
```

使用项目Python标准库 `sqlite3.Connection.backup()` 从 `data/app.db` 创建备份；不要新增仓库脚本，使用一次性只读/备份命令即可。备份完成后记录：

- 绝对路径
- 文件大小
- SHA-256
- 源库与备份库 `PRAGMA quick_check`
- 升级前Alembic版本

不得把备份加入Git，不得删除任何旧备份。

## 正式升级

仅在全部安全门禁通过后执行：

```powershell
& $python -m alembic upgrade head
```

随后必须验证：

```powershell
& $python -m alembic current
& $python -m alembic heads
& $python -m alembic check
```

并通过SQLAlchemy/SQLite只读检查确认：

- `journal_metric_import_batches`存在。
- `literature_commercial_journal_metrics`包含新字段。
- `alembic_version`等于唯一head。
- `PRAGMA foreign_key_check`返回空集合。
- `PRAGMA quick_check`返回`ok`。
- 升级前已有关键表行数没有减少；至少对检索任务、检索结果、知识源、文档等升级前存在的业务表记录升级前后行数并比较。

## 冒烟验收

不要导入任何虚构数据。使用升级后的正式库进行只读冒烟：

1. 应用导入与路由注册成功。
2. `GET /api/v1/journal-metrics/imports`返回成功；没有真实导入时允许返回空列表。
3. 读取现有文献检索历史成功。
4. 对现有结果页抽查一条；没有激活指标批次时，论文仍正常返回且指标状态为 `not_configured`。
5. 不调用真实PubMed网络，不调用云端模型，不写入测试论文或指标。

冒烟可使用项目现有TestClient/ASGI测试工具，但必须连接正式数据库并保持请求只读。禁止用会自动创建、删除或覆盖数据库的测试fixture。

## 失败处理

- 升级前失败：停止，不改变正式数据库。
- 升级命令失败：保留原库和备份，记录完整错误；不得连续盲目重试。
- 升级后任一完整性检查失败：停止应用，保留失败现场；不要直接覆盖正式库。报告备份路径和建议恢复步骤，等待用户确认后再恢复。
- 不得在本任务中执行 `alembic downgrade` 作用于正式库。
- 不得未经确认用备份覆盖正式 `data/app.db`。

## 验收条件

- AC-A1：升级前存在一致性备份，SHA-256与路径已记录。
- AC-A2：正式库从旧revision升级到唯一head。
- AC-A3：`alembic check`通过。
- AC-A4：SQLite `quick_check=ok`且`foreign_key_check`为空。
- AC-A5：新表和新列存在。
- AC-A6：升级前已有关键业务表行数未减少。
- AC-A7：期刊指标批次列表API只读冒烟成功。
- AC-A8：既有检索历史/结果仍可读取。
- AC-A9：未配置指标时结果页诚实返回`not_configured`。
- AC-A10：未修改前端，未导入虚假数据，未删除备份。

## 最终输出

只在AC-A1至AC-A10全部满足后声明“正式数据库启用完成”，并报告：

- 升级前后revision
- 备份路径、大小和SHA-256
- SQLite完整性检查结果
- 新表/字段检查结果
- 关键表升级前后行数
- 冒烟接口结果
- 真实执行命令及退出状态
- 当前尚未导入真实指标数据
- 前端仍待下一阶段实现

任何AC失败时不得声明完成。
