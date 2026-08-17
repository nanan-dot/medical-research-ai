# 素问·知识库/文档库页面优化执行提示词（FE-KNOWLEDGE-20260813）

> 本提示词由 Hermes 生成（基于设计审核 + 代码规范 + 前端工程标准），供 Codex 执行。
> 执行前必须先读仓库规范与现状，再动手。

## 一、任务总览

优化「文档与知识」页面的两个 tab（知识库 / 文档库）：
1. **修复代码规范问题**（当前代码是单行压缩风格，违反 CODE_STANDARDS）
2. **前端设计优化**（信息可视化/状态呈现/可访问性）
3. **禁止**新增功能逻辑、禁止改 API 契约、禁止伪造数据

## 二、必读文件（执行前按序阅读）

1. `docs/CODE_STANDARDS.md` — 代码生成强制规范 V2.0（42 条，最高规范，必须服从）
2. `frontend/src/components/knowledge-source/KnowledgeSourceManager.vue` — 知识库 tab 主组件（**重点优化对象**）
3. `frontend/src/components/knowledge-source/KnowledgeSourceList.vue` — 来源卡片列表
4. `frontend/src/components/knowledge-source/KnowledgeSourceForm.vue` — 添加抽屉表单
5. `frontend/src/views/Documents/DocumentsView.vue` — 文档库 tab（DocumentManager）
6. `frontend/src/views/KnowledgeBase/KnowledgeBaseView.vue` — 知识库独立页（含 workflow-footer）
7. `frontend/src/components/document/DocumentManager.vue` — 文档库主组件
8. `frontend/src/api/knowledgeSources.ts` + `frontend/src/api/documents.ts` — 真实 API 契约
9. `frontend/src/composables/useKnowledgeSources.ts` — 数据层 composable
10. `frontend/src/styles/tokens.css` — 设计 tokens（语义颜色/圆角/阴影）

## 三、背景：页面现状与设计意图

「文档与知识」是**单页双 tab**（页面内局部导航，非左侧一级导航变化）：
- **知识库 tab**：管理"资料文件夹"（来源）——添加/同步/启停/统计（文件数/已索引/异常）
- **文档库 tab**：管理"文件夹里的具体文件"——解析/索引状态/重试/预览/上传

设计图已确认 = 现状形态。**你的任务不是重做布局，是修复质量 + 打磨细节**。

## 四、任务一：代码规范修复（必须做，Highest）

### 1.1 抽取模板内联对象（CODE_STANDARDS 第 9 条：消魔法数字/魔幻字符串）
`KnowledgeSourceManager.vue` L55 的 `v-for="filter in [{ value: 'all', label: '全部' }, ...]"`：
- **问题**：每次渲染创建新数组（性能）+ 数据散落模板（可维护性）
- **修复**：提到 script 顶部为具名常量：
```ts
const SOURCE_FILTERS: ReadonlyArray<{ value: SourceFilter; label: string }> = [
  { value: "all", label: "全部" },
  { value: "enabled", label: "已启用" },
  { value: "errors", label: "异常" },
  { value: "recent", label: "最近同步" },
];
```

### 1.2 格式化单行压缩代码（CODE_STANDARDS 第 4 条：可读性 > 炫技）
以下文件存在**超长单行**（>200 字符），必须拆为多行、语义化缩进：
- `KnowledgeSourceManager.vue` L55/L59/L62/L63（template）
- `KnowledgeSourceManager.vue` L68+（style 单行）
- `DocumentManager.vue` 全文（template 单行压缩）
- `KnowledgeSourceList.vue` 全文（如存在单行）
- `DocumentsView.vue` / `KnowledgeBaseView.vue` 的 style

**规则**：
- 拆行后保持功能不变（diff 只应有空白/换行变化，不应有逻辑变化）
- 中文注释保留
- 用项目现有风格（与 `frontend/src/components/home/ResearchStartPanel.vue` 等多行风格一致）

### 1.3 颜色统一为语义 token（frontend-ui-engineering）
`KnowledgeSourceManager.vue` CSS 里硬编码的 `#fff` / `#10213d` / `#fafcff` / `rgba(16,33,61,...)`：
- **修复**：改用 `tokens.css` 已有变量（`--surface` / `--ink-900` / `--surface-muted` / `--shadow-card` 等）
- 先读 tokens.css 确认变量名，**不要发明新变量**
- 若 tokens.css 缺某个语义（如 drawer 阴影），可加一个命名合理的变量并在注释说明

### 1.4 原生 window.confirm 替换（frontend-ui-engineering：生产级 UI）
`KnowledgeSourceManager.vue` L40 `window.confirm`：
- **问题**：原生弹窗与产品视觉割裂、无键盘/ARIA 一致性
- **修复**：改为**组件内确认态**——点击"移除"后按钮变成"确认移除？"（二次点击才执行），
  或做一个轻量确认浮层（不引入新依赖，纯 Vue 实现）
- 若改动成本高，可降级为：保留 confirm 但加 `aria-label` 说明（至少标注）

## 五、任务二：前端设计优化（按可行性排序）

### 2.1 异常来源的错误摘要行（设计优化，优先做）
`KnowledgeSourceList.vue` 的异常来源卡片（sync_status = completed_with_errors/unavailable）：
- 在卡片内加一行**错误摘要**（如红色小字）：从 source 的真实字段读取（如 `last_sync_error` 或类似），
  **没有该字段就显示通用文案**"同步存在问题，请查看详情"（不伪造具体错误）
- **先读 `frontend/src/api/knowledgeSources.ts` 的类型定义**确认有哪些字段可用

### 2.2 同步状态的可视化
- 当前是静态"等待同步"标签。**检查 `KnowledgeSource` 类型是否有 sync 进度字段**：
  - 有 → 显示真实进度（如"同步中 45%"）
  - 无 → **保持诚实**，只做视觉层级优化（标签颜色/图标），**禁止伪造进度条**

### 2.3 文档库 tab 的 AI 检索框真实性确认
`DocumentManager.vue` 的"AI ⌕"搜索框：
- **确认它是否调用真实接口**（文档导航检索，`documentNavigation` 相关 API）
- 若已接真实接口：不动（或只优化视觉）
- 若是占位/no-op：**保持诚实**——禁用或显示"请输入检索内容"引导，**禁止假装有结果**

### 2.4 空态与加载态
- 知识库无来源时：显示引导空态（"添加第一个资料文件夹开始"）+ 主按钮
- 加载中：用骨架屏（frontend-ui-engineering 要求）而非文字"正在读取"

### 2.5 可访问性（WCAG）
- 所有 icon-only 按钮有 `aria-label`（检查 `×` 关闭按钮等）
- filter-tabs 的 `role="tablist"` 需要配套 `aria-selected`（当前只有 class active）
- 颜色不只传达状态（异常红字旁加图标或文字）

## 六、⚠️ 工作区边界（最高优先级）

- 仓库可能已有未提交改动（其他会话进行中）——**执行前先 `git status` 查看**：
  - 若工作区干净 → 正常执行
  - 若有不属于本次任务的文件 → **只修改下列白名单文件，其余一律不碰**
- **只允许修改**：
  - `frontend/src/components/knowledge-source/KnowledgeSourceManager.vue`
  - `frontend/src/components/knowledge-source/KnowledgeSourceList.vue`
  - `frontend/src/components/knowledge-source/KnowledgeSourceForm.vue`
  - `frontend/src/views/KnowledgeBase/KnowledgeBaseView.vue`
  - `frontend/src/views/Documents/DocumentsView.vue`
  - `frontend/src/components/document/DocumentManager.vue`
  - （若确需微调）`frontend/src/styles/tokens.css` — 仅当确缺语义变量
- **禁止修改**：`AppSidebar.vue`、`AppTopbar.vue`、`features.ts`、`router/index.ts`、所有 API 文件（只读）、所有后端文件
- 提交时只 add 上述白名单文件，**绝不用 `git add -A`**

## 七、验收标准（必须全部真实运行并报告输出）

```bash
cd /h/AI_project/rag_medicine/frontend
npm run typecheck   # 0 错误
npm run test        # 全部通过（现有 39 files / 79 tests 不许减少）
npm run build       # 构建成功
npx eslint src/     # 0 errors（新代码不得引入 error）
```

- **不修改任何功能行为**：筛选/排序/添加/同步/启停/移除/跳转文档库 全部保持原行为
- **不破坏测试契约**：`KnowledgeSourceManager.test.ts`（如存在）现有断言必须通过
- **不新增依赖**：禁止 `npm install` 任何包（纯 Vue/CSS 实现）

## 八、交付说明（完成后输出）

1. 修改文件清单（每个文件：改动类型 + 行数统计）
2. 任务一（规范修复）逐项说明：抽了什么常量 / 格式化哪些文件 / 换了哪些 token / confirm 怎么处理
3. 任务二（设计优化）逐项说明：异常摘要怎么做的 / 同步进度有无真实字段 / AI 检索框是否真实
4. 验证命令真实输出（typecheck/test/build/eslint）
5. 边界确认：只改了白名单文件，未碰 API/路由/后端
6. 已知限制与【未实测】项

## 九、禁止事项

- ❌ 不新增功能逻辑（不改筛选逻辑、不加新 API 调用、不加新状态流）
- ❌ 不修改 API 契约（knowledgeSources.ts / documents.ts 只读）
- ❌ 不伪造数据（进度/错误/结果，无真实字段就保持诚实空态）
- ❌ 不重做布局（tab 结构/卡片结构保持现状，只打磨）
- ❌ 不用 `git add -A`
- ❌ 不提交、不推送（只改工作区）
