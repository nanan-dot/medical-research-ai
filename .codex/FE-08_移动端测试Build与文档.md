# FE-08：移动端、测试、Build与交付文档提示词


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
你现在执行FE-08：移动端、全局测试、Build与前端交付文档。

本轮不增加新的业务页面，只进行收尾、修复和验收。

一、全局审查

检查FE-01—FE-07所有页面：

- 是否使用统一AppShell；
- 是否复用Design Token；
- 是否存在超大页面组件；
- 是否有重复API逻辑；
- 是否有大量any；
- 是否有硬编码颜色和间距；
- 是否有无意义注释；
- 是否存在无调用代码；
- 是否有Mock冒充LIVE；
- 是否有假医学数据；
- 是否缺少Loading、Empty、Error和Retry。

二、移动端

至少适配：

- 375px；
- 430px；
- 768px；
- 1024px；
- 1440px。

移动端策略：

- 左侧导航改Drawer或底部导航；
- 右侧Context Rail改底部抽屉；
- 文档和问答优先；
- 多论文比较改字段视图；
- 证据矩阵以只读和轻量编辑为主；
- 写作和组会支持查看、轻量编辑和待确认；
- Agent移动端仅查看和审批；
- 评测移动端只显示关键指标。

不要强行把桌面三栏压缩成三列手机页面。

三、可访问性

检查：

- 键盘导航；
- focus-visible；
- 图标按钮名称；
- 表单Label；
- 对比度；
- 状态不只依赖颜色；
- reduced motion；
- Dialog焦点管理；
- 表格语义；
- Skip Link；
- 错误提示关联；
- 屏幕阅读器文本。

四、性能

检查：

- 路由懒加载；
- 大表格虚拟化；
- 图片尺寸；
- 不必要重渲染；
- 请求取消；
- 防重复提交；
- Skeleton；
- 大依赖；
- Bundle分析；
- 本地缓存边界。

不要进行没有数据依据的复杂优化。

五、测试

完善：

- 基础组件测试；
- 页面组件测试；
- Store测试；
- API Adapter测试；
- Mock Adapter测试；
- LIVE/MOCK/UNAVAILABLE测试；
- 关键用户流程E2E。

关键E2E：

流程A：
首次进入 → 模型设置 → 添加知识源 → 查看文档。

流程B：
文档详情 → 论文分析 → 点击引用 → 创建组会入口。

流程C：
证据问答 → 无答案 → 反馈。

流程D：
文献主题 → 条件建模 → 同义词/MeSH → 检索式预览。

流程E：
创建组会原型 → 编辑提纲 → 保存草稿。

六、实际命令

根据仓库真实脚本运行：

- type-check；
- lint；
- unit test；
- component test；
- e2e；
- build；
- preview smoke test。

不得虚构通过。

七、交付文档

更新或创建：

docs/frontend/
- FRONTEND_README.md
- FRONTEND_ARCHITECTURE.md
- FRONTEND_ROUTE_MAP.md
- FRONTEND_FEATURE_MATRIX.md
- FRONTEND_API_INVENTORY.md
- FRONTEND_MOCK_BOUNDARIES.md
- FRONTEND_TEST_REPORT.md
- FRONTEND_ACCESSIBILITY_REPORT.md
- FRONTEND_IMPLEMENTATION_STATUS.md

文档必须说明：

- 如何安装；
- 如何启动；
- 如何配置API Base；
- 如何切换Mock；
- 当前LIVE能力；
- 当前原型能力；
- 已知限制；
- 下一步如何随着R2-WP03推进接入PubMed。

八、最终验收报告

输出：

1. 页面清单；
2. 路由清单；
3. LIVE/MOCK/UNAVAILABLE矩阵；
4. 移动端结果；
5. 可访问性结果；
6. 性能结果；
7. 实际命令；
8. 测试结果；
9. Build结果；
10. 已知限制；
11. 未完成项；
12. Git提交建议。

完成后停止，不进入新的后端或前端阶段。
```
