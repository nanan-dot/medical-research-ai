# 素问·移除文档库直接上传入口（FE-KNOWLEDGE-REMOVE-UPLOAD-20260813）

> 本提示词由 Hermes 基于用户需求 + 项目现状生成，供 Codex 执行。
> 执行前必须先读仓库规范与现状，再动手。**只做第一阶段（移除入口）**。

## 一、任务总览

移除文档库（/documents）中的**直接上传 PDF 入口**，撤销相关前端调用链。
**不删除**后端 `/api/v1/document-uploads` 接口、不删除已有"上传文档"知识源、不删除任何数据。
**不做**单篇文档导入的新功能（那是下一阶段）。

## 二、必读文件（执行前按序阅读）

1. `docs/CODE_STANDARDS.md` — 代码生成强制规范 V2.0（42 条，最高规范，必须服从）
2. `frontend/src/components/document/DocumentManager.vue` — 主修改对象（注意：**当前工作区已有未提交的格式化改动**，在其之上增量修改）
3. `frontend/src/components/document/DocumentManager.test.ts` — 测试（含 1 个上传测试需移除）
4. `frontend/src/api/documentUploads.ts` — 后端上传 API（**只读，不删**）
5. `frontend/src/composables/useDocumentUpload.ts` — composable（**保留文件，不再从 DocumentManager 引用**）
6. `frontend/src/components/document/DocumentUploadPanel.vue` — 组件（**保留文件，不再从 DocumentManager 引用**）

## 三、⚠️ 工作区边界（最高优先级）

**当前有 8 个未提交文件（其他会话进行中）——必须保留，不执行 git reset/checkout，不 stash：**
```
M .codex/FE-13-*.md
M frontend/src/components/document/DocumentManager.vue   ← 已有格式化改动（单行拆多行）
M frontend/src/components/knowledge-source/KnowledgeSourceForm.vue
M frontend/src/components/knowledge-source/KnowledgeSourceList.vue
M frontend/src/components/knowledge-source/KnowledgeSourceManager.vue
M frontend/src/views/Documents/DocumentsView.vue
M frontend/src/views/KnowledgeBase/KnowledgeBaseView.vue
```

**你只允许修改 3 个文件**：
1. `frontend/src/components/document/DocumentManager.vue`
2. `frontend/src/components/document/DocumentManager.test.ts`
3. `frontend/src/components/document/DocumentUploadPanel.test.ts`（**仅当**它因 DocumentManager 改动而失效；若独立可跑则不动）

**禁止触碰**：知识库相关文件（KnowledgeSource*）、DocumentsView/KnowledgeBaseView、API 文件、路由、后端、`useDocumentUpload.ts`、`DocumentUploadPanel.vue`（保留文件本身）。

## 四、具体修改（A 部分）

### 1. DocumentManager.vue
移除以下**所有**与直接上传相关的内容：
- `import DocumentUploadPanel from "./DocumentUploadPanel.vue";`
- `import { useDocumentUpload } from "../../composables/useDocumentUpload";`
- `const { uploading, error: uploadError, uploadedFilename, uploadedDocument, upload } = useDocumentUpload();`
- `async function uploadPdf(file: File): Promise<void> { ... }` 整个函数
- `requestError` computed 里的 `?? uploadError.value ??` 合并项
- 模板里的 `<DocumentUploadPanel ... @upload="uploadPdf" />` 及其 props

**保留**：资料范围、文件列表、DocumentFilters、单篇解析/索引/重试、批量索引、详情面板、分页、`sourceId` URL 筛选逻辑、`loadSources`、`currentSource`。

**注意**：模板**必须保持当前多行格式**（不要退回单行，不要重新格式化整个文件——只删上传相关行）。

### 2. DocumentManager.test.ts
- 移除 `it("uploads a PDF and reloads the document list", ...)` 整个测试块（L117 起）
- **保留**其余所有测试（失败状态/重试解析、状态筛选等）
- 若测试文件顶部有仅上传测试使用的 import（如 `File` 相关），一并清理；不确定就保留

### 3. DocumentUploadPanel.test.ts
- 先运行它：若独立通过 → **不动**
- 若它 import 了 DocumentManager 或依赖上传流程 → 按最小改动适配（不删除组件本身）

## 五、禁止事项

- ❌ 不删除 `DocumentUploadPanel.vue`、`useDocumentUpload.ts`、`documentUploads.ts` 文件（保留供未来阶段使用）
- ❌ 不改后端任何代码
- ❌ 不删除/修改"上传文档"知识源或数据库数据
- ❌ 不在文档库添加任何"占位替代"功能（本阶段就是移除，不替换）
- ❌ 不新增依赖、不引入 mock
- ❌ 不用 `git add -A`（只 add 你改的 3 个文件）
- ❌ 不提交、不推送

## 六、验证要求（必须真实运行并报告）

```bash
cd /h/AI_project/rag_medicine/frontend
npm run typecheck                     # 0 错误
npx vitest run src/components/document/DocumentManager.test.ts   # 通过（3 个测试，上传测试已移除）
npx vitest run src/components/document/DocumentUploadPanel.test.ts  # 独立可跑则通过
npm run build                         # 构建成功
```

**代码检查确认**（grep）：
```bash
grep -n "DocumentUploadPanel\|useDocumentUpload\|uploadPdf" src/components/document/DocumentManager.vue
# 应无输出（DocumentManager 不再引用）
```
⚠️ 后端 `/api/v1/document-uploads` 仍存在**不是失败**——那是预期保留。

## 七、交付报告格式

1. 实际修改文件清单（3 个以内）
2. 页面效果：文档库不再有"上传 PDF/上传文档"入口
3. 明确说明：已有"上传文档"知识源和文件未被删除（未执行任何删除）
4. 测试命令与真实输出（typecheck/vitest/build/grep）
5. 下一阶段设计建议（只写说明，不实现）：
   - 单篇文档导入放"知识库→导入资料"流程
   - 选项 1：导入文件夹；选项 2：导入单篇文档
   - 导入单篇必须选择归属：归入已有知识库文件夹，或用户命名创建可见容器
   - 禁止静默创建"上传文档"来源；导入后在文档库按"知识源/子目录/文件"组织
