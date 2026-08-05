# FE-01：Design System与应用外壳提示词


## 全阶段共同背景

项目：医学科研智能助手平台  
当前后端进度：**R2-WP02 已完成**  
前端目标：先完成整体产品界面，再随着后端任务推进逐步替换 Mock Adapter。

必须区分三种功能状态：

- `LIVE`：仓库中已经存在并经过验证的真实接口；
- `MOCK`：高保真前端原型，使用类型安全的 Mock Adapter；
- `UNAVAILABLE`：当前不能合理模拟的能力，明确显示“待接入”，不得伪装成功。

R2-WP03及之后、R3、R4的后端能力，在仓库没有真实接口时不得擅自补写后端，不得把 Mock 医学数据包装成真实检索结果。

视觉参考文件建议放在：

```text
docs/design/医学科研智能平台界面总览.png
```

总体风格：

- 月之暗面式稳定产品结构；
- 深海军蓝左侧导航；
- 浅色论文纸张感工作区；
- Awwwards/Behance的构图与留白；
- Dribbble级组件细节；
- Nature、Science、PubMed式医学科研专业感；
- 统一右侧证据与上下文栏；
- 禁止普通后台模板、同质Card墙、廉价霓虹和无意义特效。

共同代码规则：

1. 一个文件只负责一个功能；
2. 禁止所有代码写在一个文件；
3. 每个组件独立封装；
4. 复杂逻辑添加有意义的中文注释；
5. 使用TypeScript；
6. API、Types、Store、Composable、View分层；
7. 不生成无意义代码和未来空壳；
8. 不伪造医学论文、DOI、PMID、页码、统计数据和真实接口结果；
9. 实际运行类型检查、Lint、测试和Build；
10. 未实际运行的命令不得声称通过；
11. 每轮只完成当前FE任务；
12. 完成后立即停止，不自动进入下一任务。


---

# 可直接复制给Codex

```text
你现在执行FE-01：Design System与应用外壳。

前置条件：

- FE-00已经完成；
- FRONTEND_API_INVENTORY、FEATURE_MATRIX和IMPLEMENTATION_PLAN存在；
- 已确认真实前端技术栈；
- 本任务不实现完整业务页面。

一、任务目标

建立可供全部后续页面复用的：

- Design Token；
- AppShell；
- 左侧主导航；
- 顶部工具栏；
- 面包屑；
- 全局搜索入口；
- 快速创建菜单；
- 任务状态入口；
- 模型与隐私状态；
- 统一右侧Context Rail；
- 响应式导航；
- Feature Flag；
- LIVE/MOCK/UNAVAILABLE功能标签；
- API Adapter和Mock Adapter边界；
- 路由元数据结构。

二、视觉要求

参考最终草图，但不要像素级复制。

视觉方向：

- 深海军蓝左侧导航；
- 浅灰白论文纸张背景；
- 白色主内容面；
- 医疗蓝主操作；
- 蓝青色证据；
- 绿色完成；
- 琥珀色待确认；
- 克制红色错误；
- 细边框和留白优先；
- 玻璃效果只用于局部浮层；
- 首页以编辑式构图为主；
- 业务页强调证据和效率。

三、导航结构

工作台

论文与知识
- 知识源
- 文档库
- 论文分析
- 证据问答

文献研究
- 文献检索
- 收藏与阅读计划
- 多论文比较
- 证据矩阵

研究与表达
- 研究方向
- 组会汇报
- 写作项目
- 引用核验

高级工具
- Agent实验室
- 质量评测

底部：
- 任务中心
- 反馈与帮助
- 设置

未完成阶段的菜单根据Feature Flag隐藏或显示“原型”标签，不显示无意义空页面。

四、建议文件职责

具体路径以FE-00审查结果为准，建议：

frontend/src/
- layouts/AppShell.vue
- components/layout/AppSidebar.vue
- components/layout/AppTopbar.vue
- components/layout/ContextRail.vue
- components/layout/MobileNavigation.vue
- components/layout/Breadcrumbs.vue
- components/layout/QuickCreateMenu.vue
- components/layout/GlobalSearchDialog.vue
- components/system/FeatureStatusBadge.vue
- components/system/ModelPrivacyStatus.vue
- styles/tokens.css
- styles/base.css
- router/index.ts
- router/route-meta.ts
- types/feature.ts
- config/features.ts
- api/http-client.ts
- api/adapters/
- mocks/

一个文件一个主要职责，不要将全部布局写入App.vue。

五、基础组件

只实现后续必需组件：

- Button；
- IconButton；
- Input；
- Select；
- Badge；
- StatusBadge；
- Tabs；
- Tooltip；
- Dialog；
- Drawer；
- Toast；
- Skeleton；
- EmptyState；
- ErrorState；
- Progress；
- ConfirmDialog。

不要提前创建几十个无人使用的组件。

六、功能状态

实现统一状态：

LIVE
MOCK
UNAVAILABLE

Mock页面必须有清晰的“前端原型”提示。

七、路由

建立路由元数据：

- title；
- breadcrumb；
- phase；
- featureStatus；
- showInNavigation；
- requiresContextRail；
- mobileSupport。

只创建必要占位路由壳，不创建完整业务页面。

八、测试

至少覆盖：

- AppShell渲染；
- 导航分组；
- Feature Flag隐藏；
- LIVE/MOCK标签；
- 移动端导航；
- Context Rail开关；
- 键盘打开全局搜索；
- reduced motion基础行为。

九、验收

- 视觉与草图方向一致；
- 页面外壳不使用普通后台模板；
- 导航可以折叠；
- 顶部模型和隐私状态可见；
- 右侧栏可按页面切换；
- 移动端可导航；
- 类型检查、Lint、测试和Build真实通过；
- 更新FRONTEND_IMPLEMENTATION_STATUS。

完成后只说明下一步FE-02，不执行。
```
