# R1 实施状态

## 当前工作包

- 工作包：R1-WP07《论文问答与引用》
- 状态：已完成
- 负责模块：论文问答与引用

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

### R1-WP04

- 定义与第三方库隔离的 `ParsedDocument`、`ParsedPage`、`ParsedSection` 和解析器协议。
- PDF 使用 pypdf 逐页提取并保留 1-based 页码、空页和标题候选；基础移除跨页重复首尾行。
- PDF 低文本量时明确返回 `is_scanned=true`，不执行 OCR，也不伪造文本。
- Markdown 严格按 UTF-8/UTF-8 BOM 解码，解析 YAML front matter、1–6 级标题、章节正文和来源路径。
- 非法 YAML、编码错误、100 MiB 输入限制、1000 万字符提取限制和不支持类型均使用稳定错误状态。
- 解析在工作线程中执行，成功持久化统一 JSON 并把索引标记 `outdated`；失败写入 WP03 状态机。
- 新增解析和内容摘要接口；摘要不返回完整正文。

### R1-WP05

- 将 Document ID 映射到 PaperQA2 索引键，并持久化 PaperQA2 版本与已索引文件哈希。
- 提供单文档、批量和删除索引接口；批量逐项返回结果，单项失败不阻塞后续文档。
- 成功且哈希、版本均匹配时直接复用；文件变化标记 `outdated`，版本变化强制重建。
- 同一进程内按文档加锁，拒绝并发重复索引；PaperQA2 异常进入 `failed` 并保留受限错误。
- 每个文档使用独立元数据命名空间，冲突或不兼容元数据明确失败，避免索引串用。
- 删除系统索引映射不会删除或修改用户原始论文；底层不支持安全单文档删除时仅清除本系统映射。

### R1-WP06

- 新增 17 项通用单篇论文阅读报告，字段显式区分事实、总结、推断与“未找到”。
- 使用版本化 JSON 提示词和 PaperQA2 来源，逐字段校验零基来源索引，拒绝来源错配。
- 保存分析状态、文档、模板/模型版本、生成代次、结构化结果、来源与待确认项。
- 支持创建、查询、重新生成、用户字段纠错和 Markdown 导出；关键数字与来源页定位随结果导出。
- 分析失败落库为 `failed`，响应不回传模型原始内容；未完成有效索引的文档不能分析。
- Vue 新增按研究生阅读顺序展示的分析页，显示事实类别、未找到项、来源页、重生成与导出入口。

### R1-WP07

- 会话锁定 1–10 篇当前有效索引论文；多选基础问答逐篇调用 PaperQA2 并合并回答，不跨论文伪造综合结论。
- 用户和助手消息按会话内唯一序号持久化，保存模型版本、耗时及用户反馈。
- 引用独立保存文档、页码、章节、受限证据摘录和检索分数；空页码/空来源保持为空。
- 索引过期、模型失败、同会话并发消息和引用保存失败均返回明确冲突，引用失败不保留无引用助手消息。
- 提供创建、恢复、发送消息和反馈 API；Vue 聊天页支持文档选择与点击引用查看证据。

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

### R1-WP04

- 解析器与 Document 专项：31 passed。
- 全量后端回归：128 passed、5 skipped；仅有已知 Starlette TestClient/httpx2 弃用警告。
- mypy：Document 解析边界 13 个源码文件通过。
- Ruff：全仓 lint 和本轮格式检查通过。
- Alembic：upgrade→downgrade→upgrade 通过，最终 `e146f13a9c52 (head)`；`alembic check` 无差异。
- 真实夹具覆盖单栏 PDF、基础双栏、空页、无文本扫描提示、Markdown 标题/YAML/编码错误和不支持类型。

### R1-WP05

- 索引专项：8 passed，覆盖单文档、批量部分失败、失败重试、重复复用、文件变化、删除、版本变化、并发和目录冲突。
- 全量后端回归：136 passed、5 skipped；仅有已知 Starlette TestClient/httpx2 弃用警告。
- mypy：CLI、PaperQA2 适配器和索引边界共 18 个源码文件通过。
- Ruff：`app tests alembic` 全部 lint 通过。
- Alembic：upgrade→downgrade→upgrade 通过，最终 `f257a24b0d63 (head)`。
- PaperQA2 调用由 Mock 覆盖，不产生云端费用，也不伪造真实索引运行。

### R1-WP06

- 结构化分析专项：5 passed，覆盖样本量、研究类型、方法、结果、缺失字段、来源映射、重新生成、失败状态、纠错和导出。
- 全量后端回归：141 passed、5 skipped；仅有已知 Starlette TestClient/httpx2 弃用警告。
- Ruff：`app tests alembic` 全部 lint 通过；mypy 覆盖 CLI、适配器与分析模块。
- Alembic：upgrade→downgrade→upgrade 通过，最终 `a4c81d7e9201 (head)`；无新迁移差异。
- 前端：`vue-tsc` 通过；Vitest 3 个文件、5 个测试通过；Vite 生产构建通过。

### R1-WP07

- 问答专项：4 passed，覆盖单文档、多选论文、引用/空页码/超长证据、会话恢复、模型失败、索引过期和反馈。
- 全量后端回归：145 passed、5 skipped；仅有已知 Starlette TestClient/httpx2 弃用警告。
- Ruff 与 mypy 覆盖会话、适配器及迁移；Alembic upgrade→downgrade→upgrade 后为 `b8e4a9f103d2 (head)` 且无差异。
- 前端：`vue-tsc` 通过；Vitest 4 个文件、6 个测试通过；Vite 生产构建通过。

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
- PDF 双栏仅依赖 pypdf 文本层顺序，不做复杂版面恢复、表格识别、公式识别或 OCR。
- 扫描版识别采用文本量启发式；混合扫描/文字 PDF 可能需要后续逐页 OCR 策略。
- Markdown 暂不完整解析 Obsidian/Wiki 链接、嵌入、Dataview 或其他插件语法。
- 索引互斥锁为单进程内锁；多进程部署需要数据库锁或任务队列提供跨进程互斥。
- PaperQA2 当前不提供安全的单文档物理删除能力；删除接口清除本系统映射和隔离元数据，保留底层共享缓存及原论文。
- 进程中断由 WP03 的超时校正机制在后续查询时转为 `failed/task_stalled`，尚无后台巡检。
- WP06 自动化测试使用 Mock 验证结构与证据规则；尚未对 5 篇真实论文实际运行，因此“至少 5 篇真实论文”的人工验收仍需使用授权/公开论文逐篇完成，不能宣称已通过。
- 通用模板不替代专业系统综述或临床判断；不适配的论文类型会产生较多“未找到/待确认”，不会自动补写。
- WP07 未实际执行 10 个真实问题人工核对；需要在授权论文及本地模型可用时检查回答可用率和逐条引用对应关系。
- 多选论文目前逐篇回答后并列展示，不做跨论文证据综合；这符合本阶段禁止多论文证据矩阵的边界。

## 下一任务

下一工作包为 R1-WP08；在 WP07 独立提交完成前不提前实施。
