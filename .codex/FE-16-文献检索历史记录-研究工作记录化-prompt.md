# FE-16：文献检索历史记录「研究工作记录化」与有意义变化提示

## 0. 执行位置、状态与硬边界

唯一代码仓库：`H:\AI_project\rag_medicine`

开始先确认 `.git`、`frontend/package.json`、`app/` 存在，并执行：

```bash
git status --short --branch
git diff -- frontend/src/views/LiteratureSearch app/modules/literature_search
```

当前工作区混有其他并行会话的未提交改动，尤其包含知识库、Topbar、AppShell、tokens，以及刚完成的 FE-15 面包屑改动。**保留全部既有修改**。禁止：

- `git reset`、`git restore`、`git checkout --`、`git clean`、`git stash`；
- 覆盖或格式化白名单以外的改动；
- 提交、push；
- 物理删除旧任务、旧结果快照、`LiteratureSearchResultVersion`、收藏/已读/标签/阅读顺序/知识库关联；
- 重写后端检索、PubMed 执行、结果页筛选排序、收藏/已读/标签/全文逻辑；
- 新增第三方依赖、`v-html`、假论文/假任务/假时间/假统计数据。

### 需求与真实代码事实（已核查，必须以此为准）

用户已经确认：主历史页是**研究工作记录**，不是 PubMed 请求日志、版本审计表或开发调试界面。

现状：

- `app/modules/literature_search/service.py` 已有 `strategy_fingerprint()`、同策略复用 `rerun_task()`、不可变 `result_versions` 与 `_build_change()`；
- 用户态绑定 `result_id + pmid`，旧结果不可粗暴删除；
- `History.vue` 当前将 raw task 按策略分组后仍渲染 **group 内每一条审计 task**；因此同策略仍显示多行、执行次数和 v1/v2；
- `HistoryTableRow.vue` 默认显示原始 Boolean Query、版本号与任何 `change`，包括 `33 → 33 / 新增 0 / 减少 0` 的零变化；
- `_to_task_read()` 当前未把 ORM 的 `strategy_fingerprint` 显式写入 `LiteratureSearchTaskRead`，尽管 schema/API 声明该字段，必须核实并修复；
- `GET /literature-search/{id}/strategy` 已存在，可保留完整布尔检索式以支持 PRISMA/导出，不应在主历史表默认呈现。

## 1. 必读文件（全读后再写任何代码）

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/CODE_STANDARDS.md`（V2.0，42 条）
4. `app/modules/literature_search/model.py`
5. `app/modules/literature_search/schema.py`
6. `app/modules/literature_search/repository.py`
7. `app/modules/literature_search/service.py`（至少完整阅读 `strategy_fingerprint*`、`create_task`、`list_tasks`、`rerun_task`、`_build_change`、`_to_task_read`）
8. `app/modules/literature_search/router.py`
9. `tests/modules/literature_search/test_history.py`
10. `frontend/src/api/literatureSearch.ts`
11. `frontend/src/views/LiteratureSearch/History.vue`
12. `frontend/src/views/LiteratureSearch/HistoryTableRow.vue`
13. `frontend/src/views/LiteratureSearch/History.test.ts`
14. `frontend/src/views/LiteratureSearch/LiteratureSearchView.vue`
15. `frontend/src/views/LiteratureSearch/LiteratureSearchView.test.ts`
16. `frontend/src/views/LiteratureSearch/ResultsView.vue`
17. `frontend/src/styles/tokens.css`
18. 本任务提示词自身。

## 2. 产品目标与不可妥协规则

### 2.1 历史页只显示一个用户可见入口

同一策略（**服务端权威策略语义**，优先 `strategy_fingerprint`；旧行缺该字段时按与后端一致的快照规范计算）在主历史页**只能有一条可见研究记录**。该记录代表此策略的最新状态/最新结果入口。

- 不删除任何旧任务或旧快照；旧版本仍可通过已有 `GET /literature-search/{id}` 与 `/strategy` 等内部/详情契约读取；
- 主列表不得出现相同策略的多行审计记录；
- 不能只把其中一条改成 v2 而保留其他旧行；
- 不能仅在当前原始分页页内“碰巧分组”：分组与分页的顺序必须保证用户在不同页不会再次看到同策略的第二条记录；
- 不可把整份无上限历史静默加载到浏览器后再假装分页。若现有 `GET /literature-search` 的 raw-task 分页无法保证上述语义，新增一个**最小、只读、分页的服务端历史汇总 read-model endpoint/契约**；不得修改/删除任何持久化业务数据。优先复用既有 schema、service、repository 和纯函数，不造并行检索机制。

### 2.2 主表的用户语言

一条记录只呈现用户决定下一步所需的信息：

1. **研究问题**：`original_query`，作为主标题；长文本可响应式截断/自然换行，不丢失可访问名称；
2. **最新结果**：如 `最新结果 33 篇`（来自真实最新快照的 `result_count`）；
3. **状态**：`已完成 / 失败 / 执行中 / 待执行`；
4. **最后运行**：最新真实 `searched_at`；没有成功运行时保持“未检索”，不得伪造时间；
5. **操作**：`查看结果`（有真实 `latest_result_id` 时）与 `重新检索`；
6. **失败原因**：状态失败且后端真实返回 `error_message` 时才展示。

主表、分组标题、工具栏、默认折叠内容中**不得显示**：

- 完整 Boolean Query / PubMed 字段限定 / `AND` / `OR` / `[Title/Abstract]`；
- `v1/v2`、`执行 N 次`、任务 ID / 结果 ID；
- “版本变化”这个系统词；
- 任何零变化的技术信息。

本任务不新做“查看检索策略”菜单；完整检索式仍由既有 `/strategy` 接口保留给未来详情/导出，不在 UI 中杜撰入口或伪造详情。

### 2.3 变化提示只在用户可感知时出现

定义纯函数/具名 helper（前后端各自只放所属层）来判断：

```text
isMeaningfulChange(change) =
  change != null AND
  (change.added_count > 0 OR change.removed_count > 0 OR change.count_delta != 0)
```

- 三项都为 0：不渲染变化区域、不留空白、不显示“v2”“已更新”“新增 0 / 减少 0”；
- 有意义变化时，使用用户语言而非版本语言：
  - 仅新增：`本次检索发现 N 篇新增文献`；
  - 仅减少：`与上次相比，N 篇文献不再命中当前条件`；
  - 仅命中数变化且新增/减少为 0：`结果从 A 篇更新为 B 篇`；
  - 新增、减少或总数同时变化：简洁完整地说清每项实际变化；
- PMID 列表、技术版本号不进入主历史表；
- `change` 继续保留在后端响应中（审计/详情能力不破坏），只改变主历史 UI 的展示条件。

### 2.4 检索中心的同策略提示同步降噪

`LiteratureSearchView.vue` 当前 `reuseNotice` 显示“已执行 N 次 · 当前为 vN”。把它改为不暴露执行次数/version：

- 若 reused 且有**有意义变化**：显示以上用户语言的短提示；
- 若 reused 但没有变化：不显示提示；
- 若 created：不额外造提示；
- 保持真实的 `activeResult` 跳转和 `previousResultId`/结果查看行为，不改检索请求和后端执行。

## 3. 设计与可访问性约束（frontend-design / frontend-ui-engineering / web-design-guidelines）

- 页面单一工作：帮助研究者找回一个研究问题，并继续“查看结果 / 重新检索”；不要把它设计成卡片瀑布、系统日志或仪表盘；
- 高级科研产品的克制密度：研究问题为强信息锚点，元信息紧凑为辅助行，操作靠右但不抢视觉；避免大面积阴影、渐变、无意义编号、过度圆角；
- 表头改为对用户有意义的列：`研究问题 | 最新结果 | 状态 | 最后运行 | 操作`。不得保留“检索式 / 结果版本”列；
- 仅使用 `tokens.css` 已有语义 token 和项目既有 spacing/radius，禁止裸 hex、`rgba` fallback、`var(--x, #hex)`、`transition: all`；
- 色彩不单独表达变化/状态，保留中文文字；
- `button` / `RouterLink` 语义正确、键盘可访问、`:focus-visible` 清晰；保留桌面与 ≤900px 窄屏布局（窄屏按信息优先级排，不横向强塞技术列）；
- 保留现有 LIVE 真实数据边界，不硬编码任何疾病、药物、论文、PMID、时间或结果数字；
- 不改 AppSidebar、AppTopbar、面包屑、一级导航、Topbar CSS、token 定义、路由表。

## 4. 架构与 API 契约约束

在 `commentary` 先输出：

1. 当前 raw task → 版本 → 用户态的数据关系图；
2. 你选择的“服务端聚合 vs 前端聚合”方案及理由；
3. 它如何保证分页后同策略仍只有一条可见记录；
4. 旧快照/收藏/已读/标签/阅读顺序为何不会丢失；
5. 预期改动文件清单。

### 若需要服务端只读历史汇总契约

- 先定义清晰、最小的 Pydantic response model 与匹配 TypeScript 类型；
- 新字段保持加法兼容；**不得**删改已有 `GET /literature-search` 的 response shape；
- endpoint 用复数/资源语义的现有风格，并有 typed 参数与分页；
- 不泄露 `strategy_fingerprint`、version、result ID 等内部字段到主列表 UI；
- 计算分组 key 时必须复用 `strategy_fingerprint_from_snapshot()`，不要在前端或另一后端文件复制一套近似序列化逻辑；
- 选择最新代表记录的排序必须确定（成功/失败和时间边界都要测试）；
- 新 endpoint 的历史数据扫描若不能服务端正确分页，不得退化为前端无上限加载；说明并实现可扩展的 repository 查询方案。若发现无迁移无法做到正确持久化聚合，先停止并报告设计阻断，**不得**删除或重写旧关联数据。

### 已知需要核实的后端缺口

`_to_task_read()` 目前没有传入 `strategy_fingerprint`。若核实属实，修复此 response 映射并加回归测试；这是已声明 schema 契约的缺失字段，不是新业务字段。

## 5. TDD：必须可见 RED → GREEN

对每个垂直行为切片先测试、运行确认失败，再实现最小代码、再运行变绿。把具体 RED/GREEN 命令与结果写到最终报告；若 agent 环境无法运行命令，明确标注【未执行】，但不得伪造。

### 后端验收（若后端 read-model 或映射修复发生）

1. 创建相同策略两次 → 原任务/旧结果版本都保留，用户可见历史列表只返回一条，且其 `latest_result_id` 指向真实最新快照；
2. 两个语义不同策略 → 返回两条；
3. legacy 行无 `strategy_fingerprint` 仍按后端同一 canonical 规则归并，绝不删除；
4. 分页跨界场景：同策略 raw task 位于不同原始排序位置时，用户可见分页中仍最多一条；
5. `LiteratureSearchTaskRead` 返回真实 `strategy_fingerprint`（若实体有值）；
6. 旧 `GET /literature-search`、创建、重跑、导出策略、收藏/已读/标签既有测试不回归；
7. 结果完全相同的重跑仍创建不可变快照，但变化摘要保留 0 值（只是不应由主 UI显示）。

### 前端验收

1. 同策略两条 raw/审计任务 → 历史页只显示一条 `.history-item`，链接指向最新真实 `latest_result_id`；不显示 `执行`、`v1/v2`、Boolean query、`[Title/Abstract]`；
2. 不同策略 → 都展示；
3. 零变化 `{ count_delta: 0, added_count: 0, removed_count: 0 }` → 页面没有 `.change-summary`/变化文案；
4. 新增、减少、仅总数变化、混合变化 → 各自呈现正确的中文用户提示；
5. `result_count`、状态、日期和失败原因来自 fixture/API，不伪造；
6. 无 `latest_result_id` 时不渲染“查看结果”；运行中重跑禁用；
7. `LiteratureSearchView` reused 零变化不显示 notice；有变化显示用户语言，不显示版本/执行次数；
8. 现有 `?tab=history` 深链、FE-15 `from=history` 结果页链接与返回历史记录行为不回归；
9. 关键 controls 可键盘访问，状态不只靠颜色。

Vue 测试使用真实 router + `flushPromises`；更新旧测试断言为新用户意图，不能简单删测试来绿灯。

## 6. 文件边界

### 允许修改（按实际最小方案，非全部必改）

前端：

- `frontend/src/api/literatureSearch.ts`
- `frontend/src/views/LiteratureSearch/History.vue`
- `frontend/src/views/LiteratureSearch/HistoryTableRow.vue`
- `frontend/src/views/LiteratureSearch/History.test.ts`
- `frontend/src/views/LiteratureSearch/LiteratureSearchView.vue`
- `frontend/src/views/LiteratureSearch/LiteratureSearchView.test.ts`
- 上述组件的同目录新建、单一职责的 `*.vue` / `*.ts` / `*.test.ts`（仅确有必要时）

后端（**仅在实现正确的服务端只读聚合/修复已声明 response 映射时**）：

- `app/modules/literature_search/schema.py`
- `app/modules/literature_search/repository.py`
- `app/modules/literature_search/service.py`
- `app/modules/literature_search/router.py`
- `tests/modules/literature_search/test_history.py`

### 明确禁止修改

- 任意 migration、数据库 model、`app/core/models.py`、`app/api/v1/__init__.py`；
- `frontend/src/router/*`、`AppTopbar.vue`、`AppSidebar.vue`、`Breadcrumbs.vue`、`AppShell.vue`、`tokens.css`、`package.json`；
- `frontend/src/views/LiteratureSearch/ResultsView.vue` 与 FE-15 相关文件（只可读/回归验证）；
- 任意 knowledge_source/Document 相关文件；
- 任何测试 fixture 的真实外部网络调用。

如果正确实现确实要求触碰禁止文件（例如 migration），**停止并报告理由与替代方案**，不要越权。

## 7. 质量门与真实验证

逐条真实运行（Windows/git-bash）：

```bash
cd H:\AI_project\rag_medicine
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest tests/modules/literature_search/test_history.py -q
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest -q
ruff check app/modules/literature_search tests/modules/literature_search
# 仅若改动后端类型：
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m mypy app/modules/literature_search --ignore-missing-imports

cd H:\AI_project\rag_medicine\frontend
npm run typecheck
npm test -- --run
npm run build
npx eslint src/views/LiteratureSearch src/api/literatureSearch.ts

cd H:\AI_project\rag_medicine
git diff --check
git diff --stat HEAD
git status --short --branch
```

浏览器验收（前后端运行时）必须验证真实历史数据；不能写入虚构数据污染开发库：

1. 历史记录主表默认不含 raw Boolean Query、版本、执行次数；
2. 确认同策略只见一个入口；
3. 确认零变化没有变化提示；
4. 确认有真实变化时文案面向用户；
5. 点击查看结果、重新检索、再回历史记录，验证 FE-15 面包屑不回归；
6. 1440px 与窄视口检查文字截断/换行、无技术列横向溢出、键盘聚焦可见。

## 8. 最终报告（完成即停止，不提交）

1. 数据关系与最终聚合方案（说明为何不删除旧快照）；
2. 改动文件及逐文件职责；
3. RED → GREEN 证据；
4. 每项质量门的实际命令与原始摘要；
5. 浏览器验收与【未实测】项；
6. `git diff --stat HEAD`、`git status --short --branch`；
7. 白名单外既有改动清单，并明确未触碰；
8. 已知限制与后续建议（只有真实存在时）。
