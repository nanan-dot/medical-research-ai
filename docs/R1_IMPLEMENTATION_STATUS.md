# R1 实施状态

## 当前工作包

- 工作包：R1-WP03《文档状态与任务管理》
- 状态：已完成
- 负责模块：文档状态与任务管理

## 前置条件

- R0 阶段验收已通过，证据见 `docs/R0_ACCEPTANCE.md`。

## 范围

- 本工作包只实现本地文件夹、Obsidian Vault 和临时导入目录的登记、校验、启停与移除系统记录。
- 不执行文件扫描、索引、PaperQA 问答、PubMed、写作、Agent 或多用户部署。

## 已完成

### R1-WP01

- 完成 `knowledge_sources` 数据字段、唯一规范化路径和 Alembic 迁移。
- 支持本地文件夹、Obsidian Vault、临时导入目录三种来源。
- 规范化 Windows 大小写、盘符和冗余段；解析符号链接后保存真实路径。
- 创建时检查目录存在、类型和可读性；权限问题返回 403，网络/设备临时不可用返回 503，重复目录返回 409。
- 已登记目录移动或短暂不可用时，查询会保留记录并标记 `unavailable`；恢复后回到 `idle`。
- 支持列表、创建、详情、名称/启停修改和移除系统记录；删除不读取或删除原始文件。
- 新建 Vue 3 + TypeScript 最小知识源页面，包含三类来源表单、状态列表、启停、移除和错误展示。

### R1-WP02

- 支持递归扫描 PDF、Markdown、DOCX 和 TXT，并忽略 `.obsidian`、`.git`、`.trash`。
- 使用 1 MiB 固定块流式计算 SHA-256，避免把大文件一次载入内存。
- Document 保存知识源、相对路径、规范化路径、SHA-256、大小、纳秒修改时间和扫描状态。
- 首次文件创建 `pending` 记录；内容变化更新摘要并标记 `outdated`；只变时间时更新元数据但计为跳过；未变化文件不重新建档。
- 删除文件只删除数据库中的 Document 记录，不删除或修改授权目录原文件。
- 单文件读取失败、扫描中消失、路径过长或目录暂时不可用均按 `OSError` 边界隔离；失败不会阻塞其他文件，也不会误删受影响的旧记录。
- 符号链接必须解析后仍位于授权根目录；同一物理文件的多路径通过设备/文件标识去重。
- 同步摘要持久化新增、修改、删除、跳过、失败数量和最后同步时间。
- 新增同步与状态接口：`POST /api/v1/knowledge-sources/{id}/sync`、`GET /api/v1/knowledge-sources/{id}/sync-status`。

### R1-WP03

- 增加解析状态 `pending/parsing/succeeded/failed` 和索引状态 `pending/indexing/succeeded/failed/outdated`。
- 增加错误码、受限错误消息、重试次数、任务开始与完成时间。
- 使用独立状态机拒绝非法转换；解析或索引运行中禁止重复重试并返回 409。
- 解析仅允许失败后重试；索引仅允许失败/过期且解析成功后重试，重试只重新排入 `pending`。
- 运行超过 30 分钟且没有完成报告的任务自动校正为 `failed/task_stalled`。
- 源文件被外部删除时，解析标记 `failed`、索引标记 `outdated`，避免失败仍显示成功。
- 错误消息压缩为单行、限制 500 字符，并脱敏常见 Key、Token、Password 和 Secret。
- 状态变化日志仅记录文档 ID、任务、前后状态，不记录文件正文或错误原文。
- 文档列表支持解析/索引状态过滤、总数和基础 offset/limit 分页；提供详情、解析重试、索引重试和删除系统索引接口。
- Vue 前端新增文档状态页、双状态标签、错误展示、过滤、分页、重试和删除索引操作。

## 测试结果

### R1-WP01

- 知识源后端测试：10 passed、1 skipped；skip 为当前 Windows 账户无符号链接权限时的环境条件分支。
- 全量后端回归：89 passed、4 skipped；仅有已知 Starlette TestClient/httpx2 弃用警告。
- mypy：知识源与异常边界 7 个源码文件通过。
- Ruff：`app tests scripts alembic experiments` 全部 lint 通过。
- Alembic：独立数据库 upgrade→downgrade→upgrade 通过，最终 `b741bb1a6d5c (head)`；`alembic check` 无差异。
- 前端：`vue-tsc` 类型检查通过；Vitest 1 个文件、2 个测试通过；Vite 生产构建通过。
- npm audit：0 vulnerabilities。

### R1-WP02

- 同步专项：8 passed、1 skipped；skip 为当前 Windows 账户无文件符号链接权限时的环境条件分支。
- 全量后端回归：97 passed、5 skipped；仅有已知 Starlette TestClient/httpx2 弃用警告。
- mypy：扫描、同步、Document 和路径工具共 16 个源码文件通过。
- Ruff：`app tests scripts alembic experiments` 全部 lint 通过。
- Alembic：独立数据库 upgrade→downgrade→upgrade 通过，最终 `c824d91e7a30 (head)`；`alembic check` 无差异。

### R1-WP03

- Document 专项：18 passed。
- Document + Sync 组合：26 passed、1 skipped。
- 全量后端回归：115 passed、5 skipped；仅有已知 Starlette TestClient/httpx2 弃用警告。
- mypy：Document 与同步边界 8 个源码文件通过。
- Ruff：`app tests scripts alembic experiments` lint 和本轮格式检查通过。
- Alembic：upgrade→downgrade→upgrade 通过，最终 `d935e02f8b41 (head)`；`alembic check` 无差异。
- 旧数据映射：WP02 `scan_state=outdated` 升级后得到 `parse_status=pending`、`index_status=outdated`、`retry_count=0`。
- 前端：`vue-tsc` 通过；Vitest 2 个文件、4 个测试通过；Vite 生产构建通过。

## 已知限制

- 本工作包只登记和管理授权目录，不扫描文件、不建立索引，也不触发 PaperQA。
- 浏览器安全模型不能直接读取任意本地绝对路径，因此页面收集路径文本，由后端在本机验证；未实现原生目录选择器。
- Windows 的 ACL 判定最终以实际打开目录为准；测试使用确定性 Mock 覆盖拒绝访问。
- 网络盘状态在读取知识源列表或详情时刷新，未实现后台心跳或自动同步。
- R1-WP01 阶段的 `last_sync_time` 为后续同步预留并保持为空。
- R1-WP02 已开始写入 `last_sync_time` 和最近一次同步统计，但不保存完整历史运行列表。
- `outdated` 仅表示后续索引必须重建；本工作包没有向量索引实现，因此不会伪造“已重建”状态。
- 同步接口当前为单进程内同步执行，没有后台任务队列、进度百分比或跨进程锁。
- 文件类型按扩展名筛选，不在本工作包校验 PDF/DOCX 内部格式或提取正文。
- WP03 只管理任务状态与重试入队语义，不包含真实解析器、向量索引或后台任务执行器。
- `started_at/finished_at` 当前描述最近一次解析或索引任务，不保存完整状态变更历史；可审计历史需要后续独立任务表。
- 卡死任务在文档列表或详情查询时校正，没有后台定时巡检。
- 删除索引当前清除索引状态并回到 `pending`；尚无独立向量存储可删除。

## 下一任务

等待明确的下一工作包文档；不提前实现正文解析、真实索引、检索或 Agent。
