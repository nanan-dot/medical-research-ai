# 素问·科研工作台前端整体重建执行方案

> 这是可执行工程文档。目标是在不修改后端、数据库、Alembic迁移和用户数据的前提下，冻结旧前端并从新骨架重建全部Vue页面。  
> 代码仓库：`H:\AI_project\rag_medicine`  
> 前端范围：`H:\AI_project\rag_medicine\frontend`  
> 设计规范：`.ulpi/design/DESIGN.md`

## 1. 授权边界

本方案只允许修改、移动、替换或删除：

```text
frontend/
```

为了保存设计规范、执行记录和验收报告，允许新增：

```text
.ulpi/design/
docs/frontend-rebuild/
```

明确禁止修改：

```text
app/
alembic/
data/
uploads/
tests/ 后端测试
.env
任何用户授权的医学文档目录
```

发现后端接口不足时，只记录为 `BACKEND_REQUIRED`，不得在本任务中补后端，也不得使用Mock冒充。

## 2. 核心决定

重建不是直接执行递归删除，而是：

```text
审计旧前端
  ↓
建立可恢复Git快照
  ↓
记录API/路由/业务契约
  ↓
冻结旧frontend
  ↓
创建全新frontend骨架
  ↓
逐工作包恢复真实功能
  ↓
全量验收
  ↓
最后删除旧前端副本
```

任何阶段失败都必须能回到旧前端。没有可验证快照时禁止删除。

## 3. 删除前硬门禁

执行者必须先完成以下检查：

1. 读取仓库 `AGENTS.md` 和 `docs/CODE_STANDARDS.md`；
2. 读取 `.ulpi/design/DESIGN.md`；
3. 完整列出 `frontend/src`、`frontend/public`、配置和测试；
4. 记录当前 `git status --short`；
5. 区分用户已有未提交修改，不得覆盖或丢弃；
6. 运行旧前端基线：`npm test`、`npm run typecheck`、`npm run build`；
7. 导出真实路由清单、API模块清单、组件引用关系和功能清单；
8. 检查后端 OpenAPI 或Router，形成“页面→真实接口”矩阵；
9. 记录所有其他模块指向 `/documents`、`/analysis` 等前端路由的链接；
10. 创建用户可恢复的Git分支或提交，并验证提交ID存在。

如果工作区包含无法区分归属的前端修改，停止删除并报告冲突，不得运行破坏性命令。

## 4. 安全快照

优先使用Git保存旧版本：

```powershell
Set-Location H:\AI_project\rag_medicine
git status --short
git switch -c frontend-rebuild-v2
```

只有用户明确授权提交时才创建提交。没有提交权限时，将旧前端移动为仓库内明确的临时目录：

```text
.frontend-legacy-snapshot/
```

移动前必须解析并核对绝对路径：

```text
源：H:\AI_project\rag_medicine\frontend
目标：H:\AI_project\rag_medicine\.frontend-legacy-snapshot
```

必须确认：

- 源目录严格等于上述 frontend；
- 目标目录不存在；
- 目标仍位于仓库根目录内；
- 不使用通配符；
- 不使用 `$HOME`、`~` 或未解析变量；
- 不执行 `git reset --hard`；
- 不执行针对仓库根目录的递归删除。

快照未验证可读取前，不得创建替代性空目录覆盖旧前端。

## 5. 必须从旧前端提取的契约

即使页面代码全部重写，也必须先记录并重新实现这些契约：

### 5.1 构建契约

- Node/npm版本；
- `package.json` scripts；
- Vite配置；
- TypeScript配置；
- Vitest配置；
- 环境变量名称；
- `/api/v1`代理策略；
- 构建输出目录。

### 5.2 路由契约

至少记录：

- 路径；
- 路由名称；
- 参数和query；
- 懒加载边界；
- 面包屑；
- 旧链接来源；
- 新版本是否保持兼容。

旧URL必须优先兼容。确需更名时添加重定向，不允许静默404。

### 5.3 API契约

每个现有API模块记录：

- Endpoint；
- Method；
- Request；
- Response Type；
- 错误结构；
- 使用页面；
- LIVE/BACKEND_REQUIRED/DEFERRED。

新前端不得通过猜测字段、解析错误文本或制造随机数据补齐接口。

### 5.4 业务契约

必须保存：

- 文献检索条件和历史；
- 文献结果、去重、阅读顺序；
- 知识来源CRUD和同步；
- 文档浏览、解析、索引、预览、OCR、批注；
- 论文分析和证据问答；
- 证据矩阵；
- 研究方向、可行性和导师审阅；
- 写作项目、版本、引用证据和AI披露；
- 汇报大纲与演示文稿；
- 任务中心、设置和反馈。

任何旧模块若不在本轮恢复，必须列为DEFERRED并提供诚实不可用页面，而不是从导航中无声消失。

## 6. 新前端技术基线

```text
Vue 3
Composition API
<script setup lang="ts">
Vue Router
Vite
Vitest
Vue Test Utils
TypeScript strict
```

设计系统：

- 使用 `.ulpi/design/DESIGN.md` 锁定token；
- 复杂无障碍交互优先使用 Reka UI primitives；
- 不引入第二套组件系统；
- 不复制粘贴组件库源码伪装自研；
- 图标只使用一个图标族；
- 不引入Tailwind，除非执行前证明它能降低而非增加迁移复杂度并获得用户同意。

依赖规则：

1. 先检查旧依赖是否仍有真实用途；
2. 新增依赖必须说明用途、体积和替代方案；
3. 锁文件必须同步；
4. 禁止同时保留两个完成相同工作的库；
5. 不为单个简单控件引入大型依赖。

## 7. 新目录结构

```text
frontend/
├─ public/
├─ src/
│  ├─ app/
│  │  ├─ App.vue
│  │  ├─ router.ts
│  │  └─ routeMeta.ts
│  ├─ assets/
│  │  ├─ tokens.css
│  │  ├─ reset.css
│  │  └─ base.css
│  ├─ api/
│  │  ├─ client.ts
│  │  ├─ errors.ts
│  │  └─ modules/
│  ├─ components/
│  │  ├─ ui/
│  │  ├─ layout/
│  │  └─ feedback/
│  ├─ composables/
│  ├─ features/
│  │  ├─ home/
│  │  ├─ literature-search/
│  │  ├─ knowledge-base/
│  │  ├─ document-library/
│  │  ├─ paper-analysis/
│  │  ├─ evidence/
│  │  ├─ research-design/
│  │  ├─ writing/
│  │  ├─ presentations/
│  │  ├─ tasks/
│  │  └─ settings/
│  ├─ types/
│  ├─ utils/
│  ├─ views/
│  └─ main.ts
├─ tests/
├─ index.html
├─ package.json
├─ tsconfig.json
├─ vite.config.ts
└─ vitest.config.ts
```

规则：

- View只组合feature，不承载大段业务；
- API请求集中于api层；
- 状态和副作用集中于composable；
- 展示组件使用typed props和typed emits；
- 不建立全局God Store；
- 只有跨多个feature的稳定状态才进入全局store；
- 不在组件内散落后端URL；
- 不在模板内执行复杂排序和过滤。

## 8. 设计方向与页面家族

设计必须绑定 `.ulpi/design/DESIGN.md`。

### 8.1 应用壳层

包含：

- 左侧主导航；
- 面包屑与页面上下文；
- 全局搜索入口；
- 后台任务和通知入口；
- 用户与设置入口；
- 移动端导航Drawer；
- 跳到主内容的Skip Link。

主导航不得一次平铺所有功能。使用不超过5个主要分组，并在组内展开科研工作流。

### 8.2 页面家族

1. 工作台：研究继续、最近任务、快速入口；
2. 文献发现：检索中心、结果、历史、推荐；
3. 文档与知识：知识库、文档库、文档详情；
4. 论文与证据：论文分析、问答、证据矩阵、多论文比较；
5. 研究设计：方向、条件、可行性、导师评审；
6. 写作与汇报：写作项目、编辑器、引用核查、汇报大纲；
7. 系统：任务、模型设置、反馈。

这些页面必须共享同一壳层、状态语言、表格、按钮、Drawer、空状态和错误语气。

## 9. 状态模型

每个异步页面都必须显式支持：

```text
idle
loading
success
empty
partial
error
refreshing
submitting
```

禁止：

- API失败后显示Mock数据；
- 用空数组同时表示尚未加载和真实空状态；
- 用随机百分比伪造任务进度；
- 把技术异常原文直接展示给用户；
- 请求竞争导致旧响应覆盖新状态。

请求必须支持取消或请求序列控制。组件卸载后不得继续写入状态。

## 10. URL与导航

可分享和可恢复的状态应写入URL：

- 当前tab；
- 来源或文档ID；
- 搜索词；
- 筛选和排序；
- 页码和页大小；
- 当前分析子视图。

规则：

- 浏览器前进/后退有效；
- 刷新恢复上下文；
- 无效参数安全回退；
- 旧URL添加兼容重定向；
- 不在watch之间制造路由循环；
- 不把敏感全文、密钥或医学隐私信息放入URL。

## 11. 无障碍和交互质量

1. 语义HTML优先；
2. 所有输入有可关联label；
3. 所有图标按钮有可访问名称；
4. 完整键盘路径；
5. 可见焦点；
6. Dialog/Drawer焦点进入、陷阱、Esc关闭、焦点恢复；
7. 动态错误和结果使用适当live region；
8. 状态不只使用颜色；
9. 对比度满足WCAG AA；
10. 移动端触控目标至少44×44px；
11. reduced motion有效；
12. 数据表格保留正确表头和选择语义；
13. 不使用未净化v-html；
14. 键盘可以操作导航、菜单、分页、表格和Drawer。

## 12. 分阶段工作包

不得一轮同时重写全部模块。按工作包执行，每个工作包独立验收。

### FE-R0：基线冻结与契约盘点

交付：

- 旧前端快照；
- 路由清单；
- API能力矩阵；
- 页面/组件/测试清单；
- 未提交修改报告；
- 基线测试结果。

门禁：可从快照恢复旧前端，并重新跑通旧build。

### FE-R1：新骨架与设计系统

交付：

- Vite/Vue/TypeScript/Vitest骨架；
- locked tokens；
- Button、IconButton、Input、Select、Checkbox、StatusBadge、Table、Pagination、Drawer、Dialog、Dropdown、Skeleton、EmptyState、ErrorState；
- 应用壳层和响应式导航；
- 全局错误边界和404。

门禁：基础组件单测、键盘测试、typecheck和build通过。

### FE-R2：文档与知识

顺序：

1. 知识库；
2. 文档库；
3. 文档详情、预览、OCR、批注；
4. 知识来源与文档跳转闭环。

以已有知识库和文档库融合提示词为页面规格。不得新增导入边界冲突。

### FE-R3：文献发现

实现检索中心、检索结果、筛选、去重、阅读顺序、历史和推荐。保留真实PubMed/本地接口状态，不伪造论文。

### FE-R4：论文与证据

实现单篇论文分析、证据问答、多论文比较和证据矩阵。所有结论保持来源定位和不确定性表达。

### FE-R5：研究设计

实现研究条件、研究方向、可行性评分和导师评审。区分AI建议、人工修改和最终确认。

### FE-R6：写作与汇报

实现写作项目、版本编辑、证据绑定、AI披露、引用核查和汇报大纲。不得伪造引用或医学结论。

### FE-R7：工作台、任务与设置

实现首页工作台、任务中心、模型设置、反馈以及全局导航收口。

### FE-R8：兼容清理与旧前端删除

只有所有必须模块通过验收后才能执行：

- 全量路由扫描；
- 全量API调用扫描；
- 新旧功能矩阵对比；
- 全量测试；
- 生产构建；
- 关键页面视觉截图；
- 从Git快照恢复演练。

确认无回退需求后，才允许删除 `.frontend-legacy-snapshot`。删除前再次解析绝对路径并确认它严格位于仓库根目录。

## 13. 每个工作包的执行模板

每个工作包必须按以下顺序：

1. 读取 `.ulpi/design/DESIGN.md`；
2. 读取对应产品文档、预览图和真实代码契约；
3. 输出不超过15项计划；
4. 建立能力矩阵；
5. 提取Given/When/Then验收标准；
6. 每条AC映射至少一个测试；
7. 先写失败测试并确认RED；
8. 实现最小可用行为；
9. GREEN后重构；
10. 截图检查桌面、平板和移动端；
11. 修复无障碍和视觉问题；
12. 执行定向与全量验证；
13. 更新进度和验收追踪；
14. 停止，不自动进入下一工作包。

## 14. 总体验收标准

### AC-01 可恢复

Given旧前端已经冻结；When新骨架无法构建；Then可从Git快照完整恢复旧前端。

### AC-02 只改前端

Given查看Git diff；Then除允许的设计/报告文档外，不包含app、alembic、data和用户文件修改。

### AC-03 API真实性

Given任一页面；When请求失败；Then显示错误和重试，不回退Mock。

### AC-04 路由兼容

Given旧版公开路由和跨模块链接；When打开；Then进入对应新页面或明确兼容重定向。

### AC-05 类型安全

Given所有API响应；Then有明确TypeScript类型，不使用大面积any或类型断言掩盖错误。

### AC-06 统一设计语言

Given任意两个页面并排；Then使用同一palette、字体、radius、motion、icon和voice。

### AC-07 无虚假科研数据

Given空库或接口不可用；Then不显示虚假论文、DOI、PMID、统计和处理进度。

### AC-08 状态完整

Givenloading、empty、partial、error和success；Then各页面都有明确且不同的呈现。

### AC-09 URL恢复

Given可分享页面状态；When刷新或前进后退；Then恢复当前上下文。

### AC-10 请求竞争

Given快速搜索或切换筛选；When旧请求晚返回；Then不覆盖新结果。

### AC-11 键盘可用

Given只使用键盘；Then能完成主导航、筛选、表格操作、菜单和Drawer流程。

### AC-12 焦点管理

Given打开和关闭Dialog/Drawer；Then焦点进入、受限并返回触发位置。

### AC-13 响应式

Given1440、1024、768和390视口；Then核心操作可达且无整体横向溢出。

### AC-14 旧能力覆盖

Given旧功能矩阵中的必须项；Then新前端均有LIVE实现或得到用户批准的DEFERRED结论。

### AC-15 构建门禁

Given最终交付；Then tests、typecheck、lint（若存在）和build真实通过。

### AC-16 删除安全

Given准备删除旧前端副本；Then目标绝对路径已核对、Git快照可恢复且新前端全量验收通过。

## 15. 验证命令

```powershell
Set-Location H:\AI_project\rag_medicine\frontend
npm test
npm run typecheck
npm run build
```

如果新 `package.json` 包含 lint：

```powershell
npm run lint
```

还必须从仓库根目录运行：

```powershell
Set-Location H:\AI_project\rag_medicine
git status --short
git diff --stat
rg -n "TODO|FIXME|MOCK|mockData|Math.random|setTimeout" frontend/src
```

`setTimeout` 可以用于防抖或测试，但必须逐项解释，不能用于伪造后台任务完成。

## 16. 视觉验证

每个主要页面至少检查：

- 1440×900；
- 1024×768；
- 768×1024；
- 390×844；
- loading；
- 空状态；
- API错误；
- 长标题和长路径；
- Drawer打开；
- 键盘焦点。

截图保存到：

```text
docs/frontend-rebuild/screenshots/<work-package>/
```

不得用设计稿冒充实现截图。

## 17. Design Pre-Flight

- [x] 设计身份已锁定到 `.ulpi/design/DESIGN.md`；
- [x] 使用一个accent、一个radius scale、一个icon family和一个type pairing；
- [x] 禁止紫蓝发光、玻璃卡片、嵌套卡片和假数据；
- [x] 状态模型覆盖loading、empty、partial、error和success；
- [x] 键盘、焦点、ARIA、对比度和reduced motion已规定；
- [x] 页面采用壳层、状态条带、表格/列表、Drawer等不同布局家族；
- [x] 单视图一个主操作，复杂能力渐进披露；
- [x] “证据路径线”是唯一Signature。

自评：

| 维度 | 分数/4 | 说明 |
|---|---:|---|
| distinctive | 3 | 临床证据路径作为跨模块签名 |
| hierarchy | 4 | 工作区优先，来源和详情降权 |
| consistency | 4 | DESIGN.md锁定全部核心token |
| accessibility | 4 | 键盘、焦点、语义和对比度均进入门禁 |
| state coverage | 4 | 全局状态模型和分阶段AC完整 |
| copy quality | 3 | 专业平实，后续页面需继续校对 |
| restraint | 4 | 单一signature，禁止装饰堆叠 |
| motion | 4 | 低强度且有reduced motion |
| 总分 | 30/32 | 无维度低于3 |

## 18. Build Handoff

目标工程代理：Vue 3 / Vite高级前端工程代理。

执行指令：

> Implement exactly this spec. Theme Reka UI or native semantic primitives with the locked tokens in `.ulpi/design/DESIGN.md`; do not redesign the product and do not re-implement complex accessible primitives without need. Complete one FE-R work package at a time, prove RED then GREEN, run all gates, report, and stop before the next package.

## 19. 最终报告格式

```markdown
# 前端整体重建实施结果

## 当前工作包
## 修改与删除文件
## 旧前端恢复点
## API能力矩阵
## 路由兼容结果
## 组件与页面
## Acceptance Traceability
| AC | 测试 | 结果 |
## 实际验证命令
## 视觉验证截图
## BACKEND_REQUIRED
## DEFERRED
## 已知限制与未实测项
## 是否允许进入下一工作包
```

## 20. 开始执行

从FE-R0开始。只审计、冻结和建立恢复点，不立即删除旧前端，不编写新页面，不进入FE-R1。完成FE-R0全部门禁并提交报告后停止，等待用户确认下一阶段。
