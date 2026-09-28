---
feature: versioned-core-reading-plan
status: locked-for-preview
design_system: Reka UI primitives themed with .ulpi/design/DESIGN.md
backend_revision: c6d7e8f9a0b1
---

# 阅读计划 V2 设计规格

## Design Read

把几百篇检索结果压缩成一条可信、可调整的四阶段阅读路径；页面第一眼回答“我现在应该读哪一篇”，而不是展示一个统计仪表盘。

本页面绑定 `.ulpi/design/DESIGN.md`。Every screen must read as the same product if placed side by side.

## 事实边界

- 只使用 PubMed 元数据、摘要状态、Publication Type、MeSH、已保存的 OpenAlex 信号和已配置期刊指标。
- 不声称取得、解析或阅读了受限全文。
- 不展示后端没有提供的预计阅读时长。
- 缺失 IF、JCR、WoS、中科院分区和文章评分时显示“未配置”或“未采集”，不得显示为 0。
- 阅读状态只有“未读”和“已读”；已读时可展示 `read_at`。
- 公共阶段固定为：建立证据全貌、理解临床决策、核验一手研究、追踪最新进展。

## 主页面信息架构

### 1. Research Context

沿用检索结果页标题、研究路径和检索时间。当前步骤为“阅读计划”。右侧只保留“查看检索策略”和“返回全部文献”。

### 2. 计划状态条

单一横向状态条，不做统计卡墙：

- `12 篇核心阅读 · 3 篇已读 · 9 篇待读`
- 真实 `progress_percent` 进度条和 `3 / 12`
- `计划 v2 · 已启用`
- 主操作“调整计划”；次操作“重新规划”；三级菜单“导出 CSV / JSON、查看计划说明”

重新规划弹窗明确显示：目标核心数量 10–20、重复模式 all/consolidated、默认保留已读/重点/锁定/手工项目。

### 3. 双栏阅读工作区

左栏固定 236px，为四阶段路径；右栏为当前阶段核心阅读。取消永久右侧统计栏。

每个阶段展示：阶段名、`read_count / core_count`、`candidate_count`。当前阶段用左侧 3px accent 路径线和浅蓝背景标记。候选总数不跨阶段简单求和。

### 4. 当前阶段标题

展示阶段目标、核心/已读/候选数量。右侧唯一入口“查看本阶段候选”。候选进入 Drawer，不与核心列表混排。

### 5. 核心论文行

采用带分隔线的宽列表，不做嵌套卡片：

- 左侧 40px 顺序与拖拽柄；
- 中部为黑色论文标题、作者/期刊/年份/PMID、轻量指标标签；
- 右部 34% 为“为什么先读”，内容来自 `recommendation_reason`；
- 底部横向状态与操作：未读/已读时间、重点、锁定/手工来源、查看 PubMed、更多；
- “推荐依据”折叠后展示 `evidence_features` 和 `limitations`；
- 不提供站内全文、下载 PDF、加入知识库或进入精读按钮。

## 候选池 Drawer

宽度 720px。顶部固定显示当前阶段、搜索、年份、文献类型、JCR、WoS、中科院分区和最低 IF。列表显示后端 `CandidatePage` 的真实分页与总数。

候选操作：

- 核心未满：提升为核心；
- 核心已满：用户明确选择“扩充核心”或“替换某篇核心”；
- 可手工加入当前检索快照中的 PMID；
- 指标源未配置时禁用对应筛选并说明原因。

## 调整计划模式

进入后只增加必要控制：拖拽阶段内排序、移动阶段、锁定、降为候选、删除手工项目。保存使用完整 PMID 顺序；退出前提示未保存更改。

## 状态覆盖

- 无计划：解释将从当前检索快照生成 10–20 篇核心阅读，主操作“生成阅读计划”。
- 生成中：保留页面骨架，阶段区显示进度占位，不伪造百分比。
- 部分数据：论文仍可读，缺失指标在论文行内诚实标记。
- 404：展示无计划状态；不作为系统错误。
- 409：在候选提升/删除位置解释冲突及可选策略。
- 422：字段级校验，不清空用户设置。
- 网络错误：保留当前计划，顶部非阻塞错误条提供重试。

## 响应式

- ≥1280px：236px + 主内容双栏。
- 768–1279px：阶段路径改为横向可滚动 tabs，论文的“为什么先读”落到标题下方。
- <768px：单栏；状态条分两行；所有触控目标至少 44px；候选池为全屏 Drawer。

## 可访问性

- 四阶段使用具备 `aria-selected` 的 tabs；方向键切换。
- 进度同时提供数字，不依赖颜色。
- 拖拽必须有键盘“上移/下移”替代操作和 live region 反馈。
- 外链明确标注“在新窗口打开 PubMed”。
- Dialog/Drawer 管理焦点并在关闭时恢复。

## 验收标准

1. 页面只显示后端存在的字段和动作。
2. 四阶段顺序固定且每阶段核心/候选/已读统计来自 API。
3. 论文标题和推荐理由是前两级视觉重点。
4. 候选池与核心列表分离，并覆盖提升、扩充、替换三种行为。
5. 重新规划会明确展示版本、目标数量、重复模式和保留策略。
6. 缺失指标不伪造成 0；限制可以展开查看。
7. 已读、重点、锁定、手工来源和阶段顺序可被准确修改并持久化。
8. CSV/JSON 导出入口与后端格式一致。
9. 不出现预计阅读时间、全文获取、站内阅读和 PDF 下载能力。
10. Loading、empty、partial、404、409、422、network error、responsive 和 keyboard flow 均有验收测试。

## Pre-Flight

- [x] 绑定现有设计语言与单一 accent
- [x] 无渐变、玻璃拟态、统计卡墙和嵌套卡片
- [x] 所有主统计均有后端字段
- [x] 核心与候选职责分离
- [x] 缺失数据与限制状态完整
- [x] 桌面、平板、移动布局明确
- [x] 键盘、焦点、读屏和非颜色状态明确
- [x] 页面主问题始终是“下一篇读什么”

## Build Handoff

目标：Vue 3 `<script setup lang="ts">` 工程实现。使用 Reka UI primitives 处理 Tabs、Dialog、Drawer、Dropdown 和 Tooltip，并使用 `.ulpi/design/DESIGN.md` 的锁定 token 主题化。Implement exactly this spec. Theme the design system with our locked tokens; do NOT redesign or re-implement its components.
