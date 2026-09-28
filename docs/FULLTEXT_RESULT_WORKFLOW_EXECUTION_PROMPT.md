# Codex执行任务：打通“全部文献”页全文获取闭环

## 0. 任务目标

在仓库 `D:\AI_project\rag_medicine` 中实现“文献检索 → 检索结果 → 全部文献”页面的全文获取闭环。必须复用既有PubMed、LibraryItem、PMC官方开放全文、本地PDF上传、知识库和文档关联能力，不得另造重复系统。

最终用户在每条检索结果上能够：

1. 始终安全访问PubMed；
2. 对存在真实PMCID的文献，显式点击后尝试获取PMC官方开放全文；
3. 对需要个人/机构订阅的文献，打开系统浏览器中的PubMed或DOI页面，由用户自己登录并下载；
4. 将用户已经合法下载的PDF导入本地，并与当前文献精确关联；
5. 成功关联本地PDF后打开本地全文；
6. 不再出现“阅读计划”入口或操作。

本任务不是开发出版社账号系统，不实现付费墙绕过，不接触用户的出版社密码、Cookie或浏览器会话。

## 1. 强制工作方式

开始前完整阅读：

- `AGENTS.md`
- `docs/CODE_STANDARDS.md`
- `docs/FULLTEXT_RESULT_WORKFLOW_EXECUTION_PROMPT.md`
- 与任务直接相关的后端、前端、迁移和测试文件

使用：

- FastAPI + Pydantic v2 + SQLAlchemy 2.0异步模式；
- Vue 3 Composition API；
- `<script setup lang="ts">`；
- props down / events up；
- 复杂异步状态放入独立composable；
- 先写直接行为验收测试，再实现；
- 每个AC至少一个直接测试。

工作区已有大量用户改动和未跟踪文件：

- 禁止 `git reset`、`git checkout --`、清理未跟踪文件或覆盖用户改动；
- 只修改本任务所需文件；
- 发现重叠修改时先读取并融合；
- 不提交Git；
- 不升级正式数据库，除非本任务确实需要新增迁移且只在临时库验证；本设计原则上应优先复用现有表与字段。

## 2. 已核实的现有能力：必须复用

### 2.1 PubMed检索

- `app/integrations/pubmed/client.py`
- `app/integrations/pubmed/schemas.py`
- `app/modules/literature_search/pubmed_executor.py`
- `app/modules/literature_search/schema.py`

当前解析器会判断ArticleIdList中是否存在PMC标识，但只保留 `is_open_access: bool`，没有保留具体PMCID；`CitationItem`也没有PMCID。

### 2.2 本地收藏与PDF关联

- `POST /api/v1/literature-results/{result_id}/save`
- `POST /api/v1/library-items/{item_id}/link-local-pdf`
- `app/modules/library_item/`

当前保存服务会按PMID/DOI精确匹配已有本地文档；禁止改成标题模糊匹配。

### 2.3 PMC官方开放全文

- `POST /api/v1/library-items/{item_id}/fulltext-retrievals`
- `GET /api/v1/library-items/{item_id}/fulltext-retrievals`
- `app/modules/library_item/open_fulltext_service.py`
- `app/modules/library_item/official_pmc_client.py`
- `app/modules/library_item/open_fulltext_storage.py`
- `app/modules/library_item/open_fulltext_*`

现有实现已经包含：

- PMC OAI身份与许可核验；
- OA Web Service官方PDF地址校验；
- PMID/DOI身份一致性校验；
- 官方主机与路径白名单；
- 流式下载、大小限制、媒体类型、PDF文件头和SHA-256校验；
- Document、DocumentAsset、KnowledgeSource和获取审计持久化；
- 失败回滚及既有本地文档保护。

不得重写或弱化这些安全门禁。

### 2.4 用户PDF导入

- `POST /api/v1/knowledge-sources/import-document`
- `app/modules/knowledge_source/import_service.py`
- `app/modules/document_upload/`

已有PDF上传、结构校验、安全路径、哈希和Document/DocumentAsset创建能力。应复用，不得复制一套新的裸文件写入逻辑。

### 2.5 现有前端

- `frontend/src/components/PaperResults/PaperResults.vue`
- `frontend/src/views/LiteratureSearch/ResultsView.vue`
- `frontend/src/components/literature/PubMedLink.vue`
- `frontend/src/components/literature/FulltextAccess.vue`
- `frontend/src/components/SaveToLibrary/SaveToLibraryButton.vue`
- `frontend/src/components/SaveToLibrary/OpenAccessFulltextPanel.vue`
- `frontend/src/api/literatureSearch.ts`
- `frontend/src/api/openFulltext.ts`

不得创建与上述功能重复的第二套结果页。

## 3. 明确的业务边界

### 3.1 允许

- 访问 `https://pubmed.ncbi.nlm.nih.gov/{PMID}/`；
- 访问规范化的 `https://doi.org/{DOI}`；
- 用户在外部系统浏览器中自行登录出版社、医院、学校或机构SSO；
- 用户自行决定是否购买或下载；
- 仅在PMC官方核验全部通过后，由后端下载开放全文；
- 用户主动选择已经合法获得的本地PDF并导入；
- 对获取来源、许可、时间、失败原因进行审计。

### 3.2 禁止

- 出版社统一账号登录框；
- 保存或转发出版社账号密码；
- 读取、复制或注入浏览器Cookie；
- 内嵌WebView模拟出版社登录；
- 绕过付费墙、验证码、双因素认证或反爬机制；
- 登录后自动批量抓取出版社PDF；
- 从非官方第三方论文下载站抓取PDF；
- 把“存在PMCID”直接等同于“许可允许自动下载”；
- 页面加载时逐篇调用PMC接口；
- 自动下载当前500条检索结果。

## 4. 后端实现要求

### 4.1 打通PMCID真实数据链

在不破坏旧快照的前提下：

1. `PubMedRecord`增加：

   ```python
   pmcid: str | None = None
   ```

2. PubMed XML解析ArticleIdList：
   - 提取 `IdType="pmc"` 的真实值；
   - 统一为大写 `PMC` + 数字；
   - 缺失或非法时为 `None`；
   - `is_open_access`如保留，应由 `pmcid is not None` 派生或保持兼容，但不得继续出现两套可能矛盾的数据源。

3. `CitationItem`增加向后兼容字段：

   ```python
   pmcid: str | None = None
   ```

4. `PubMedExecutor`把PMCID写入不可变检索快照。

5. 所有旧 `items_json` 缺少PMCID时必须继续可读。

### 4.2 保存LibraryItem时保留PMCID

修改 `LibraryItemService.save_search_result()`：

- 保存真实 `citation.pmcid`；
- 同一PMID/DOI幂等返回已有LibraryItem时，如果旧记录的PMCID为空而当前快照有经过PubMed验证的PMCID，可以安全补齐，但不得覆盖不同的非空PMCID；冲突必须显式处理并记录；
- 仅存在PMCID时不得宣称PDF已下载；
- 本地PDF精确匹配逻辑保持不变。

### 4.3 结果页全文能力契约

优先以最小改动复用 `RankedCitationItem.item.pmcid`、`library_item` 和现有状态，不要为了展示再造数据库表。

如确有必要增加DTO，命名为 `FulltextCapability`，只能由现有快照和本地状态计算，至少包含：

```python
pubmed_url: str
doi_url: str | None
pmcid: str | None
local_document_id: int | None
acquisition_state: Literal[
  "not_saved",
  "not_attempted",
  "available_locally",
  "succeeded",
  "identity_mismatch",
  "license_unverified",
  "pdf_unavailable",
  "network_error",
  "rate_limited",
  "content_invalid",
  "storage_failed",
]
```

约束：

- GET检索结果不能发起PMC、出版社或DOI网络请求；
- 不得产生N+1数据库查询；
- PMID和DOI链接必须由可信标识规范化生成；
- URL不能接受任意用户主机。

如果仅靠现有字段即可实现前端状态，不要增加 `FulltextCapability`，保持KISS。

### 4.4 用户已下载PDF的“导入并关联”

先评估复用现有两步API是否能保持一致性：

1. 导入PDF，获得 `document_id`；
2. 调用 `link-local-pdf` 关联LibraryItem。

若两步失败会留下无法解释的孤立导入记录，则增加一个薄编排端点：

```http
POST /api/v1/library-items/{item_id}/import-local-pdf
Content-Type: multipart/form-data
```

实现必须委托现有导入服务和LibraryItem服务，不复制PDF安全校验及存储代码。

建议请求字段：

- `file`：必填PDF；
- `knowledge_source_id`：可选；
- `new_source_name`：可选；
- `relative_directory`：可选。

要求：

- 上传前后都不修改用户原始下载文件；
- 使用已有大小、结构、路径和哈希校验；
- 从已有Document解析结果或上传元数据按PMID/DOI精确校验；
- 当前阶段不能可靠抽取身份时，不要假装已匹配；返回明确的 `verification_required`，由用户确认后才能关联；
- 不允许仅按标题自动关联；
- 异常时数据库和文件状态必须一致；
- 不得删除用户原始文件。

如果新增端点会让本轮范围失控，则保留两步编排，但前端必须诚实报告“PDF已导入但尚未关联”，并提供继续关联入口；不可吞掉中间失败。

## 5. 前端组件设计

### 5.1 组件边界

实施前先输出组件图并遵守以下责任：

- `ResultsView.vue`：仅编排页面、分页、筛选和批量状态，不承载全文获取细节；
- `PaperResults.vue`：渲染结果列表，向子组件传递 `resultId`、citation和LibraryItem；
- `PubMedLink.vue`：只负责安全PubMed外链；
- 新建或重构 `FulltextActions.vue`：只负责单条文献全文操作UI和状态；
- 新建 `useFulltextAccess.ts`：编排保存、PMC获取、用户PDF导入、取消陈旧请求及状态刷新；
- `OpenAccessFulltextPanel.vue`：可重构为按需弹出/行内状态，但不得要求用户手工输入本应由PubMed返回的PMCID；
- API与类型留在 `frontend/src/api/`，不得在组件内裸写fetch。

### 5.2 当前“全部文献”页行为

移除：

- “阅读计划”标签；
- “加入阅读计划”；
- “进入阅读计划”；
- “已在阅读计划”；
- 与当前全部文献页面直接相关的阅读计划请求和死状态。

注意：不要在本任务中破坏其他仍独立存在的旧路由或后端阅读计划接口；只移除当前页面入口和调用。若删除全局路由会扩大范围，保留路由但不在当前页面展示。

标签建议：

```text
全部文献 | 已保存 | 重复文献
```

### 5.3 每条文献的主操作状态机

必须使用一个主操作，避免同时堆叠所有按钮：

#### A. 未保存、无PMCID

- 主操作：`访问 PubMed ↗`
- 更多菜单：`保存`、`加入知识库`、`标记已读`、`导入已下载PDF`
- 辅助文字：`外部页面 · 用户自行获取全文`

#### B. 未保存、有PMCID

- 主操作：`获取 PMC 开放全文`
- 次操作：`访问 PubMed ↗`
- 用户点击PMC操作时，可以先显式保存元数据再执行获取，但必须在UI中显示步骤和失败点；不得页面加载后自动保存或下载。

#### C. PMC核验/下载中

- `正在核验与下载…`
- 按钮禁用；
- 显示当前操作只针对这一篇；
- 页面切换或组件卸载时避免旧响应覆盖新状态；不能声称能中止已提交的服务端下载，除非后端确实支持取消。

#### D. PMC成功或已有本地PDF

- 主操作：`打开本地全文`
- 显示来源：`PMC官方开放全文`或`用户导入PDF`；
- 显示许可只使用后端真实返回值。

#### E. PMC失败

- 保留可浏览的PubMed结果；
- 根据真实状态显示：身份不匹配、许可未验证、PDF不可用、网络错误、限流、内容无效或存储失败；
- 主操作退回 `访问 PubMed ↗`；
- 提供 `导入已下载PDF`；
- 网络/限流状态允许重试，其余状态不可伪装成网络错误。

#### F. 出版社/机构订阅

- 显示 `登录后获取全文 ↗` 时，只能跳转系统浏览器中的PubMed或规范化DOI；
- 文案必须说明：`将在外部网站登录，系统不保存账号信息`；
- 不出现账号或密码输入框。

### 5.4 PDF导入交互

- 使用隐藏的 `<input type="file" accept="application/pdf,.pdf">` 或项目已有上传组件；
- 文件选择必须由用户动作触发；
- 显示文件名、上传进度/处理中、成功、失败；
- 成功后把对应结果行更新为 `打开本地全文`，无需整页刷新；
- 失败只影响当前行；
- 不使用 `v-html`；
- 图标按钮有 `aria-label`，键盘可用，焦点样式清晰；
- 外部链接使用 `target="_blank" rel="noopener noreferrer"`。

## 6. 与现有结果能力兼容

不能破坏：

- PubMed快照及最近15年边界；
- 命中总数和已加载数量；
- 筛选、facets、分页和URL同步；
- 相关度、近期热度、文章影响力、经典度及排序能力降级；
- MeSH/PICO、评分解释抽屉；
- 期刊指标IF年份、JCR、WoS和中科院分区；
- 去重工作区；
- 保存、知识库、已读、重点、标签；
- 旧检索结果快照读取；
- 正式数据库已有数据。

## 7. 验收标准

每一项必须有直接行为测试，并形成AC到测试文件/测试名的追踪表。

### AC-FT-01 PMCID解析

Given PubMed XML含合法PMC ArticleId，When解析记录，Then返回规范化真实PMCID。

### AC-FT-02 PMCID缺失

Given XML没有PMC ArticleId，Then PMCID为None，不推断、不伪造。

### AC-FT-03 快照传播

Given PubMedRecord有PMCID，When转换为CitationItem并持久化检索快照，Then读取结果仍返回同一PMCID。

### AC-FT-04 旧快照兼容

Given旧items_json不含PMCID，When读取结果，Then成功且PMCID为None。

### AC-FT-05 LibraryItem保存

Given检索条目有PMCID，When保存，ThenLibraryItem保留PMCID但不谎称PDF已下载。

### AC-FT-06 GET无外部获取

Given打开/分页/筛选结果页，WhenGET结果，Then不调用PMC、DOI或出版社接口，且查询次数不随行数线性增加。

### AC-FT-07 用户触发PMC

Given条目有PMCID，When用户显式点击获取，Then才调用现有PMC获取API。

### AC-FT-08 PMC安全门禁

身份、许可、官方地址、PDF媒体类型、文件头、大小和哈希门禁必须由现有测试继续覆盖；不得弱化。

### AC-FT-09 PMC失败降级

Given单篇PMC获取失败，Then该文献仍可访问PubMed和导入PDF，其他结果不受影响。

### AC-FT-10 用户PDF导入

Given用户选择有效PDF，When导入并完成精确身份关联，Then当前LibraryItem指向真实Document并显示打开本地全文。

### AC-FT-11 PDF中间失败

Given上传成功但关联失败，Then系统明确报告中间状态，不吞错、不谎称已关联、不删除用户原始文件。

### AC-FT-12 外部登录边界

页面只能安全打开PubMed/DOI，不渲染出版社账号密码框，不读取Cookie，不自动下载付费全文。

### AC-FT-13 页面移除阅读计划

当前全部文献页不显示或触发阅读计划入口；全部文献、已保存、重复文献视图仍可用。

### AC-FT-14 行内更新

单篇保存、PMC成功或本地导入后只更新对应行状态，不丢失当前筛选、排序和页码。

### AC-FT-15 可访问性

所有操作键盘可达；外链、文件选择、加载、成功与失败状态具有可访问名称和合适的live/alert语义。

### AC-FT-16 回归

评分、热度、期刊指标、去重、分页、筛选、保存和知识库现有直接测试继续通过。

## 8. 测试优先顺序

1. 先为AC-FT-01至AC-FT-16建立追踪表；
2. 写新增测试并确认关键测试在实现前失败；
3. 实现最小后端修复；
4. 实现API适配与composable；
5. 实现结果行交互；
6. 运行定向测试；
7. 运行后端与前端完整门禁；
8. 如浏览器控制可用，运行本地真实前后端桌面端验收并截图；不可用时明确报告，不能伪造。

建议测试位置：

- `tests/unit/test_pubmed_client.py`
- `tests/modules/literature_search/test_pubmed_executor.py`
- `tests/modules/library/test_library_item.py`
- `tests/modules/library/test_open_fulltext_service.py`
- 新增结果全文能力API验收测试文件；
- `frontend/src/components/literature/*.test.ts`
- `frontend/src/components/PaperResults/PaperResults.test.ts`
- `frontend/src/views/LiteratureSearch/ResultsView.test.ts`
- 新增 `useFulltextAccess.test.ts`。

## 9. 验证命令

遵守Windows环境约束，Python命令前清空 `PYTHONPATH`，使用项目指定解释器。

至少运行并报告：

```text
后端新增/定向pytest
后端全量pytest
ruff check（本任务及全仓适用范围）
ruff format --check
mypy（本任务后端模块及项目现有要求）
alembic heads
alembic current
alembic check
PRAGMA quick_check
PRAGMA foreign_key_check
前端ESLint（使用现有配置，不新增依赖）
npm run typecheck
npm test -- --run
npm run build
git diff --check
```

如果正式数据库不需要迁移，不得更改其revision或数据。

## 10. 完成报告格式

必须报告：

1. 审计后的实际实现方案和是否新增迁移；
2. 修改文件列表及每个文件职责；
3. AC-FT-01至AC-FT-16追踪表，包含测试文件、测试名和PASS/FAIL；
4. 实际运行的每条命令和结果；
5. 正式数据库是否变化；
6. 是否触碰外部账号、Cookie或付费全文；
7. 仍存在的真实限制。

只有全部直接AC测试、类型检查、构建和相关回归通过，才能声明“本任务全部完成”。不得把既有PMC下载骨架已经存在等同于当前结果页闭环完成。
