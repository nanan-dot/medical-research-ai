# 第六轮：真实链路与视觉测量审计

## 输入与比较前提

- 目标图：`evidence/target-current-reference.png`，1536×1024、RGB。
- 现场失败基线：`evidence/real-current-no-sidebar-baseline.png`。其研究问题为不完整的 `interstitial lung disease patients`，因此其 DISEASE 结果不能作为完整 PICO 的回归断言。
- deterministic fixture：`workspace-1536x1024.png`，1536×1024、RGB；浏览器固定 DPR 1、zoom 1、浅色模式、`document.fonts.status=loaded`、滚动位置 `(0,0)`。
- real-flow：`workspace-real-flow-1536x1024.png` 与 `workspace-real-flow-refresh-1536x1024.png`；独立 Edge profile 从入口提交完整中文问题后生成，生产 API 未被 fixture 拦截。

## 真实链路（strategy 17）

完整输入：`间质性肺疾病（ILD）患者中，抗纤维化药物的疗效与安全性如何？`

| 检查 | 实测结果 |
| --- | --- |
| parse | `model_candidate` 返回疾病、干预、结局；入口原文没有截断。 |
| expand/build | 生成 3 个概念组、9 个术语和 327 字符组合 PubMed query。 |
| create / GET | GET `/strategies/17` 返回原文、`intent_mode=pico`、9 terms、3 MeSH、revision 1。 |
| workspace / refresh | Sidebar 宽 229px；Journey 为第 3 步；刷新后原文、query、术语和唯一执行按钮仍存在。 |
| 例外 | NLM MeSH 三项均如实显示“暂不可用”；不会伪装成已验证。 |

## 1536 fixture 测量与差异

| 区域 | 锚点/状态 | changed-pixel ratio | 人工结论 |
| --- | --- | ---: | --- |
| Sidebar | 229px | 0.999748 | 壳层几何正确，品牌/图标和导航密度仍不同。 |
| Header | 75px 高 | 0.876817 | 顶部执行按钮为批准删除差异；其余排版仍需收敛。 |
| Journey | 62px 高 | 0.994657 | 圆点、连线、文字基线仍有内部差异。 |
| Basis | 196px 高 | 0.905257 | 内部卡片、字体与阴影仍不同。 |
| Terms | 386px 高 | 0.912596 | 密集 fixture 可完整显示；组内细节仍不同。 |
| Query | 98px 高 | 0.952647 | 标题/等宽文本和按钮仍不同。 |
| Limits/Ready | y=848, 80px 高 | 0.960996 | 内部内容密度仍不同。 |
| Sticky | y=937, 79px 高 | 0.877873 | 仅保留底部执行按钮；内部版式仍不同。 |

raw changed-pixel ratio 为 `0.935596`，global luminance SSIM 为 `0.281470`，edge changed-pixel ratio 为 `0.489880`。顶部批准差异遮罩只用于分析，遮罩后仍为 `0.931632`；原始 diff 继续保留为权威证据，不能据此宣称高保真完成。

## 真实页面与目标的关键差异

- 现场图缺 Sidebar 是旧/非独立 profile 页面状态证据；本轮独立 profile real-flow 已实测 Sidebar 229px 可见。
- 现场的不完整英文输入合理地产生 DISEASE/单疾病组；本轮完整输入已经产生真实 PICO、疾病/干预/结局三个组和组合 query。
- 生产少数据状态已改为内容驱动紧凑高度；fixture 的 24/10 密集状态仍固定 386px，以保持目标首屏锚点。
- 真实默认策略没有用户设置的日期、研究类型、语言和全文限制，因此 Limits 诚实显示 0 项，未用 fixture 的“4 项限制”伪造业务数据。
