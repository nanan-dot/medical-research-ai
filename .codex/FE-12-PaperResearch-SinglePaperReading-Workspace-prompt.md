# FE-12：论文研究「单篇精读」真实前端阅读工作台

## 0. 唯一目标与执行目录

**唯一代码执行根目录：`H:\AI_project\rag_medicine`**。

你当前桌面项目名可能是 `codex-richang`，但不得在其绑定的其他目录写入代码。开始前必须在终端确认：

```bash
cd H:\AI_project\rag_medicine
git status --short
```

本轮只实现 `/analysis?documentId=<真实ID>&tab=reading` 的「单篇精读」真实阅读工作台，使它与已完成的“研究概览 / 证据问答”形成连续工作流。不得重做或回退已完成的证据问答工作台。

设计方向参考（只定义信息架构和阅读语义，**不是可复制进生产页的演示数据**）：

- 用户最新参考图：`C:\Users\ADMIN\AppData\Roaming\Hermes\composer-images\composer_2026-08-11_05-54-25-389_48d52d.png`
- 旧静态方向图（如文件存在）：`H:\AI_project\rag_medicine\docs\design\论文研究_单篇精读_桌面预览_v2.png`
- 论文研究连续工作流资料：
  - `C:\Users\ADMIN\Desktop\rag医学科研项目修改1.1版\文档\前端设计\素问_论文研究_当前论文选择与连续工作流设计_2026-08-11.md`
  - `C:\Users\ADMIN\Desktop\rag医学科研项目修改1.1版\文档\前端设计\素问_论文研究_三页前端高保真设计与Mock契约.md`

若上述资料包不存在或无法读取，报告事实后继续以本仓库现有 LIVE 契约、截图和本提示词实施；不得凭空宣称读过。

---

## 1. 当前工作区的安全边界（最高优先级）

工作区已有大量来自其他任务的未提交改动和 untracked 文件。它们不是本轮资产。

1. 禁止 `git reset`、`git restore`、`git checkout --`、`git clean`、`git stash`。
2. 禁止覆盖、移动、删除、格式化或“顺手修复”非本任务文件。
3. 禁止修改后端、数据库迁移、路由定义、全局侧栏、顶栏、`package.json`、全局 token 文件、证据问答专属实现、研究概览、文献检索、推荐、OCR、写作及其他页面。
4. 禁止引入依赖；禁止提交、push。
5. 绝不硬编码或伪造真实论文、DOI、PMID、作者、期刊、页码、样本量、统计值、临床结论、分析结果、成功状态或进度。
6. 如果发现必须越界，停止并报告阻塞；不要自行扩大范围。

允许的最小白名单（优先复用，按需调整）：

- `frontend/src/views/PaperAnalysis/PaperAnalysisView.vue`
- `frontend/src/views/PaperAnalysis/PaperAnalysisView.test.ts`
- `frontend/src/components/paper/PaperAnalysisSection.vue`
- `frontend/src/components/paper/PaperHeader.vue`
- `frontend/src/components/paper/ResearchBrief.vue`
- `frontend/src/components/paper/InsightBlock.vue`
- `frontend/src/components/paper/EvidenceRail.vue`
- `frontend/src/components/paper/EvidenceCard.vue`
- `frontend/src/components/paper/SourceLocator.vue`
- `frontend/src/components/paper/paperModel.ts`
- 仅为这套阅读工作台新增的 `frontend/src/components/paper/*` 组件与同名测试
- `frontend/src/composables/usePaperResearchWorkflow.ts` 与其专属测试（**仅**在阅读态契约确有不足时）

不得触碰 `PaperEvidenceWorkspace.vue` / `usePaperEvidenceWorkspace.ts`，除非类型检查能证明本轮阅读组件与已完成证据问答有无法规避的共享类型问题；若发生，先停止报告。

---

## 2. 编码前必读与现状核对

按顺序阅读，不要仅凭截图写 UI：

1. `AGENTS.md`
2. `docs/CODE_STANDARDS.md`
3. `docs/frontend/FRONTEND_MASTER_PROMPT_R2_WP02.md`（论文分析要求）
4. `docs/frontend/FRONTEND_IMPLEMENTATION_STATUS.md`
5. `frontend/src/styles/tokens.css`
6. `frontend/src/views/PaperAnalysis/PaperAnalysisView.vue` 与测试
7. `frontend/src/composables/usePaperResearchWorkflow.ts`
8. `frontend/src/api/documents.ts`
9. `frontend/src/api/paperAnalysis.ts`
10. `frontend/src/api/conversations.ts`
11. 上述白名单内的所有现有 paper 组件
12. `frontend/src/views/Documents/DocumentDetailView.vue`、`DocumentPreviewPanel.vue`、`DocumentAnnotationWorkspace.vue`：只用于确认已有真实原文阅读/批注入口，禁止修改这些文档页文件。

在桌面会话中先简洁报告：

- 真实可读字段矩阵：`DocumentRecord`、`PaperAnalysis`、`PaperSource`、`AnalysisField`；
- 能复用的组件与复用理由；
- 原文阅读/批注现有真实路由是否已经接入；
- 本轮准确将修改/新建的文件；
- 明确不修改内容。

然后直接实施，不需要等待用户额外确认。

---

## 3. 产品与数据真实性边界

### 3.1 固定局部导航

论文研究主区域的稳定 Tab 只能是：

```text
研究概览 | 单篇精读 | 证据问答
```

- 不增加“阅读批注 / 笔记与标注”第四个 Tab。
- 单篇精读承接当前 `documentId`；切换 Tab 不得丢失该查询参数。
- “向证据问答提问”必须在 `/analysis` 内切换到现有 `tab=evidence`，不跳转为视觉脱节的旧 `/chat` 页面。

### 3.2 只渲染 LIVE 数据或诚实状态

- 当前论文标题：只用 `original_filename` 或现有真实路径回退；没有则显示“未提供”。
- 解析/索引/分析状态：只来自真实 `DocumentRecord` / `PaperAnalysis`；不造“已索引”“已解析”。
- 结构化阅读区：只基于 `PaperAnalysis.structured_result`；字段名称使用已存在 `FIELD_LABELS`，未知字段安全回退字段名。
- 每个阅读块的正文、`kind`、来源关联：只来自真实 `AnalysisField` 和 `PaperSource`。
- 来源：只显示 `excerpt`、`citation/title`、`page_start/page_end`、`score` 等 API 确实提供的字段；缺失就“未提供”。
- 无结构化结果、分析未生成、生成中、失败、文档未选、文档未研究就绪都必须是可理解的真实状态，不能用演示报告填充。
- 点击来源的页面内定位仅定位到真实右侧来源卡；不能假装能精确跳到 PDF 页。
- “打开原文批注”不能是 no-op：
  - 若检查发现既有文档详情已经真正挂载批注工作区，复用该实际入口；
  - 当前代码若仅确认 `/documents/:id?from=analysis` 可真实打开文档预览，则将动作诚实命名为“打开原文阅读”，并跳到该路由；**不得谎称已经打开批注编辑器**；
  - 不要为满足按钮文案而新接后端或越界修改文档详情页。

---

## 4. 目标信息架构与阅读交互

### 4.1 当前论文上下文条

在页面标题和局部 Tab 下方、阅读工作台前放一个紧凑的论文上下文条：

- 标识“当前论文”，展示真实标题及真实解析/索引状态；
- 长文件名可安全截断/换行，不能撑坏布局；
- “更换论文”回到 `tab=overview` 并保留当前路由语义；
- 必要时显示真实的“分析未生成/分析中/分析失败”状态；
- 不展示裸 `documentId` 给用户；不复制截图里的“设计预览论文/年份：演示”等文本。

### 4.2 1440px：阅读工作台（左 20% / 中 54% / 右 26%）

参考图的三栏结构必须保留，但不要照抄其低密度卡片样式。

**左栏：阅读目录**

- 标题为“阅读目录”；从当前 `structured_result` 的真实、非空块生成；
- 每项是原生 button，点击平滑定位中栏对应章节；激活章节应有可见状态；
- 没有结构化结果时显示解释性空态，而不是伪造固定目录；
- 目录是阅读导航，不是统计面板。

**中栏：结构化阅读报告（页面视觉主体）**

- 顶部是文章式的阅读头：报告名称、真实标题、简洁状态和真实可用操作；
- 重生成分析只在已有 LIVE API 且条件满足时保留，pending 时防止重复提交；
- 导出只保留已有真实 `paperAnalysisApi.exportUrl`；不得伪造导出成功；
- 主体为文档式章节序列，不是同质大卡片墙：使用章节序号/细分隔线/阅读行宽/低对比背景层级组织结构；
- 每章节要清楚显示：字段名称、来源语义（事实/总结/推断/原文未找到）、正文和真实来源定位；
- “推断”“原文未找到”“无来源”必须用文字与语义徽章明确提醒需回源核对，不能只靠颜色；
- 将截图中的“结果与局限”等节奏作为结构参考，但字段必须由真实 API 决定；不能硬塞截图固定字段；
- 章节级“查看证据”仅在确实有关联来源时出现，并定位右栏相应真实来源。

中栏底部放一条**连续工作流行动区**：

- “向证据问答提问”：切换到 `/analysis?...&tab=evidence`，保留 `documentId`；
- “打开原文阅读”或已核实存在时的真实批注入口；
- 不显示无调用方的“保存笔记 / 加入对比 / 生成结论”等按钮。

**右栏：来源与单篇问答**

- 标题体现“来源与单篇问答”；
- 先呈现当前选择/当前章节关联的真实来源，不足时可呈现其余真实来源，但要标明上下文；
- 每条来源呈现可审阅的短摘录、页码范围、引文信息与来源角色；不足数据均显示“未提供”；
- 右栏底部提供一个真实、明确的“向证据问答提问”操作，切换到现有 evidence Tab；
- 不伪造“来源片段 A/B”“演示章节”“匹配字段”“定位原文”等字段；
- 空来源时展示行动导向说明：当前分析没有可定位来源，建议查看分析状态/重新生成（仅在真实能力条件下）。

### 4.3 截图的视觉取舍

保留：冷白研究画布、细边框、学术蓝单一主强调、阅读目录—报告—证据的连续关系、克制操作条。

必须修正截图的低保真问题：

- 不让页面下半区留大面积无效空白；工作台以内容高度和合适最小高度支撑宽屏阅读；
- 不让中心区域像一串相同卡片；建立报告标题、章节、来源、状态之间的阅读节奏；
- 增强阅读主体的字号、行高和区块层级，避免元信息与正文同等轻薄；
- 右栏呈现“可审阅证据”，不是资料卡收集；
- 不用紫色/蓝紫渐变、霓虹、玻璃拟态、厚阴影、全页面营销 Hero、过大圆角或默认后台模板感。

视觉规则：

- 只能使用当前语义 tokens，页面局部禁止塞原始 hex；
- 主按钮只用于重生成等唯一主操作；其他动作为 outline/text；
- 文字层级建议：页面标题 28–32px，工作区标题 18–20px，正文 14–15px，元数据 12–13px；
- 间距只沿项目已有尺度（4/8/12/16/24/32）；
- 不使用 `transition: all`；若加入交互过渡，仅 transform/opacity 150–220ms，并尊重 `prefers-reduced-motion`。

### 4.4 响应式与可访问性

- ≥1440px：三栏 20/54/26；中栏优先；
- 1024–1439px：目录收窄；来源区域可移到底部，不能压缩正文到不可读；
- <1024px：单列，目录、报告、来源按阅读顺序排列，Tab 可横向滚动；
- 长内容有 `min-width: 0`、换行/截断策略，不产生横向溢出；
- 原生 `button` / `a`；动作不使用 clickable `div`；
- 所有 icon-only 按钮要有 `aria-label`；输入/异步区域使用恰当 `label`、`role=status`、`role=alert`、`aria-live`；
- 可见 `:focus-visible`，不得 `outline: none` 后无替代；
- 状态不得仅靠颜色表达；文字对比度满足可读性。

---

## 5. 组件与代码质量要求

- Vue 3 Composition API + TypeScript；禁止隐式 `any`。
- View 只负责编排/路由状态；数据派生保持在已有 `paperModel.ts` 或专属纯函数；组件各自只承担一项展示职责。
- 不把整页堆进 `PaperAnalysisSection.vue`。若该文件为适配三栏而膨胀，应按“上下文条 / 阅读目录 / 阅读报告 / 阅读来源栏”等真实职责拆出专属 paper 子组件，并为关键纯模型写测试。
- 先复用 `InsightBlock`、`EvidenceRail`、`EvidenceCard`、`SourceLocator`；只有它们无法承载本页面真实语义时才小范围调整，并在代码注释说明复用边界。
- 复杂的路由/文档切换竞态要写中文注释解释为什么，不能用复述代码的无意义注释。
- 不能为了设计改造删除尚有效的真实 API 调用、URL 恢复、已有测试或状态边界。

---

## 6. 测试要求

为阅读工作台新增/更新 Vitest 覆盖，至少覆盖：

1. `/analysis?documentId=<id>&tab=reading` 恢复真实当前文档，并读取最新真实分析；
2. 有真实结构化字段时，目录与中心章节均由真实字段生成，点击目录能调用定位行为；
3. 真实来源字段能显示，缺失页码/摘录时显示“未提供”而非伪造；
4. 无分析、分析中、失败、空 `structured_result` 各自呈现真实行动状态；
5. “向证据问答提问”保留 `documentId` 并切到 `tab=evidence`；
6. 原文阅读入口只在可用条件下提供真实路由，非 PDF/未选文档时正确禁用或给出原因；
7. 已有研究概览和证据问答 URL 恢复测试不得回归。

不要因为 jsdom 的 submit/click 限制删断言；按项目既有 Vue Test Utils 风格写可运行测试。

---

## 7. 必须真实执行的质量门

结束前必须在桌面会话中执行并报告原始结果：

```bash
cd H:\AI_project\rag_medicine\frontend
npm run typecheck
npm test -- --run
npm run build

cd H:\AI_project\rag_medicine
git diff --check
git status --short
git diff -- frontend/src/views/PaperAnalysis frontend/src/components/paper frontend/src/composables/usePaperResearchWorkflow.ts
```

此外，在不写入虚构医学数据的前提下，用实际运行的前端进行至少一次浏览器验收：

- 访问 `/analysis?documentId=<真实可用ID>&tab=reading`；
- 确认没有 documentId 时的空态；
- 若本地无真实可用文档，明确说明浏览器仅验收布局与空态，不能谎报结构化报告已经验证；
- 在 1440px 和约 1024px 各检查一次无横向溢出与三栏/堆叠行为；
- 保存一张真实截图到 `docs/design/` 或项目既有验收目录，但仅在该目录已有本轮预览资产约定时写入；否则报告截图路径，不新造设计资产目录。

如果任何命令失败，报告完整失败原因并停止；不要声称通过。

---

## 8. 最终报告格式

1. `现状与真实契约核对`
2. `设计决策：保留截图哪些语义、修正哪些低保真问题`
3. `修改文件与每个职责`
4. `真实数据 / 空态 / 错误态 / UNAVAILABLE 边界`
5. `原文阅读与批注入口的实际能力说明`
6. `实际运行命令与原始结果`
7. `浏览器与响应式实测结果`
8. `本轮刻意未触碰的文件`
9. `git diff 摘要（仅本轮文件）`
10. `已知限制【未实测】`

完成后停止。不得提交、不得 push、不得自动开始下一页。