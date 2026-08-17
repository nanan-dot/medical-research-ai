# 单篇文档导入必须归属知识库：完整执行提示词（Codex 版）

> 本提示词由 Hermes 基于用户完整需求 + 项目现状 + skills 规范生成，供 Codex 执行。
> 执行前必须先读仓库规范与现状，再动手。

## 零、必读文件（执行前按序阅读）

1. `AGENTS.md` — 项目规则（含 Windows 环境约束）
2. `docs/CODE_STANDARDS.md` — 代码生成强制规范 V2.0（42 条，最高规范）
3. `docs/design/单篇文档导入_归属知识库_设计说明.md` — 产品设计说明
4. `docs/design/知识库与文档库_页面设计说明.md` — 页面设计说明（如存在）
5. 现有代码（先读再改）：
   - `frontend/src/components/knowledge-source/KnowledgeSourceManager.vue`（主入口）
   - `frontend/src/components/knowledge-source/KnowledgeSourceForm.vue`（文件夹创建）
   - `frontend/src/api/knowledgeSources.ts` + `frontend/src/api/documents.ts` + `frontend/src/api/documentUploads.ts`（API 契约）
   - `app/modules/knowledge_source/`（router/service/repository/schema/model）
   - `app/modules/document_upload/service.py`（现有上传逻辑，含隐式来源创建）
   - `app/modules/document/model.py` + `app/modules/document_upload/model.py`（Document/DocumentAsset）
   - `tests/modules/knowledge_source/` + `tests/modules/document_upload/`（现有测试）

## 一、⚠️ 工作区边界（最高优先级）

**当前有未提交文件（其他会话进行中）——必须保留，不执行 git reset/checkout，不 stash：**
```
M frontend/src/components/document/DocumentManager.vue（上传入口已移除）
M frontend/src/components/document/DocumentManager.test.ts
M frontend/src/components/knowledge-source/KnowledgeSourceForm.vue
M frontend/src/components/knowledge-source/KnowledgeSourceList.vue
M frontend/src/components/knowledge-source/KnowledgeSourceManager.vue（+258 行重构中）
M frontend/src/views/Documents/DocumentsView.vue
M frontend/src/views/KnowledgeBase/KnowledgeBaseView.vue
?? .codex/FE-KNOWLEDGE-OPTIMIZE-20260813.md
?? .codex/FE-KNOWLEDGE-REMOVE-UPLOAD-20260813.md
```

**规则**：
- 在现有改动之上**增量修改**，不要重写整文件（除非必要）
- 提交时只 add 你改的文件，**绝不用 `git add -A`**
- 不提交、不推送

## 二、已完成内容（不要恢复）

文档库"上传 PDF"入口已移除（DocumentManager 不再引用上传组件/composable）。
**不要恢复文档库上传入口。**

## 三、产品目标

- 知识库：管理资料来源、资料文件夹、**导入入口**、同步与统计
- 文档库：管理具体文件的浏览、解析、索引、预览、详情与 AI 资料导航
- 用户可导入单篇文档，但**必须归属到一个可见知识库**；禁止自动创建"上传文档""临时文件""未知来源"等隐式知识库

## 四、用户流程（前端）

入口只放知识库页面：
```
导入资料
├─ 导入资料文件夹（保留现有创建逻辑）
└─ 导入单篇文档（新流程）
```

单篇导入三步：选择文件 → 选择归属（A 已有知识库 / B 新建知识库）→ 确认导入 → 成功跳转 `/documents?sourceId=<id>`

**归属必填**。A：下拉选已有知识库（不预选、显示名称/路径/文件数）；B：填新名称（必填、查重、原子创建）。可选 `relative_directory` 逻辑子目录（安全相对路径校验）。

## 五、后端实现（核心：新增接口）

### 5.1 新接口
```
POST /api/v1/knowledge-sources/import-document
Content-Type: multipart/form-data
file: <单文件>
knowledge_source_id: <可选>
new_source_name: <可选>
relative_directory: <可选，安全相对路径>
```

### 5.2 约束
1. `knowledge_source_id` 与 `new_source_name` **必须且只能提供一个**，否则 4xx（不保存文件/不建记录）
2. 已有知识库：校验存在 + enabled，否则 4xx
3. 新建知识库：名称必填 + 查重（重复 → 4xx 提示改名或选已有）
4. **禁止调用 `_get_or_create_upload_source`**（现有隐式来源逻辑），新接口独立实现
5. 文件存储必须在知识库受控目录内（`_safe_descendant` 可复用），不接受绝对路径
6. `relative_directory` 严格路径校验（禁 `..`/绝对路径/盘符/非法分隔符）
7. 保存：真实 knowledge_source_id、相对路径、原始文件名、sha256、大小、MIME、初始处理状态（pending）
8. **事务一致性**：文件写入 + 知识库创建 + Document 创建 + DocumentAsset 创建，任一步失败清理临时文件与已写文件；新建知识库与文档原子
9. 不删除/迁移/重命名已有"上传文档"知识源及其文件

### 5.3 建议实现位置
- 新端点放 `app/modules/knowledge_source/router.py`（或 document_upload router，但语义上归属知识源）
- service 逻辑可复用 `document_upload/service.py` 的安全校验（`_validate_file_metadata`/`_safe_descendant`/`_validate_pdf_structure`），**但不要复用 get_or_create 隐式来源**
- 检查 `app/api/v1/__init__.py` 路由注册

## 六、前端实现

### 6.1 入口改造
- `KnowledgeSourceManager.vue`：主按钮"添加资料文件夹"→"导入资料"
- 点击后显示类型选择：资料文件夹（打开现有 KnowledgeSourceForm 抽屉）/ 单篇文档（新抽屉）

### 6.2 新组件（建议拆分，遵循单文件单职责）
- `frontend/src/components/knowledge-source/SingleDocumentImportPanel.vue` — 三步编排（文件/归属/确认）
- composable（如 `useSingleDocumentImport.ts`）— 请求状态/错误/提交/成功跳转
- KnowledgeSourceManager 只负责开关与接收成功事件

### 6.3 UI 必含
- 文件名/大小/格式展示
- "已有知识库 / 新建知识库"互斥选择
- 已有知识库下拉（显示名称+路径+文件数，**默认不预选**）
- 新知识库名称输入
- 可选相对目录输入
- 归属预览：`肿瘤免疫文献 / 2026 新文献 / PD-1 联合治疗.pdf`
- 未选文件或未选归属时"开始导入"禁用
- 导入中防重复提交
- 返回真实后端错误，不伪造"解析成功/索引成功"

### 6.4 成功后
- 关闭面板、刷新知识库列表、跳转 `/documents?sourceId=<真实ID>`
- 文档库显示真实状态

### 6.5 文档库
- **不得再出现**上传 PDF/直接上传/隐式创建来源入口

## 七、格式与状态边界

- 不承诺所有格式可预览；PPTX/DOCX 的解析/索引/预览能力分别按真实能力显示
- 上传成功 ≠ 解析成功；自动解析若实现，界面显示"正在解析"（真实状态）
- 索引只能在解析成功后
- RAG 只用已解析且已索引的真实文件

## 八、测试要求（新增/更新，最小覆盖）

**后端**（`tests/modules/knowledge_source/` 或新文件）：
- 已有知识库导入成功，Document.knowledge_source_id 正确
- 新建知识库导入成功，知识库可见 + Document 归属正确
- 未提供归属（4xx）
- 同时提供两种归属（4xx）
- 不存在/停用知识库（4xx，无文件/无 Document）
- 重复新知识库名称（4xx）
- 非法相对目录/路径穿越（4xx）
- 写入失败清理/回滚
- 不自动创建"上传文档"知识源（断言无 TEMPORARY_IMPORT 来源）

**前端**（`frontend/src/components/knowledge-source/` 新测试）：
- 知识库页显示"导入资料"与两种类型
- 单篇导入未选归属无法提交
- 已有知识库提交 `knowledge_source_id`
- 新建知识库提交 `new_source_name`
- 成功后跳转 `/documents?sourceId=<id>`
- 文档库无上传入口

## 九、验证命令（必须真实运行并报告）

```bash
# 前端
cd /h/AI_project/rag_medicine/frontend
npm run typecheck
npm run test
npm run build

# 后端（项目 Python + 清空 PYTHONPATH）
cd /h/AI_project/rag_medicine
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest tests/modules/knowledge_source/ tests/modules/document_upload/ -q
# 及新增测试所在目录
```

⚠️ **如果 Codex 沙箱拒绝 pytest 写临时 SQLite**，记录"该命令未运行"并继续，不要声称通过；Hermes 会独立重跑。

## 十、最终报告格式

1. 实际修改文件清单
2. 新 API 真实请求/响应契约
3. 用户如何从知识库导入单篇文档（操作路径）
4. 如何保证文件不会落入隐式"上传文档"来源（代码证据）
5. 已有"上传文档"历史资料未被删除/迁移的说明
6. 实际测试命令与真实结果
7. 已知限制（支持格式、是否自动解析、子目录支持情况）
