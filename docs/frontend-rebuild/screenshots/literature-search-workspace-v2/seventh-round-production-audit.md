# 第七轮生产页面验收

本轮严格区分两类截图：`workspace-*.png` 是 API 被拦截的 **fixture** 视觉证据；`workspace-real-flow-*.png` 是独立 Edge profile、真实 5173/8000 API 创建的新策略证据。

- 新真实策略：`22`；原始问题为 `间质性肺疾病（ILD）患者中，抗纤维化药物的疗效与安全性如何？`。
- GET 返回：`intent_mode=pico`、疾病/干预/结局三组、9 terms、3 条 NLM unavailable 状态和组合 PubMed query；旧 DISEASE 策略没有被篡改。
- 2560×1259：Workspace 主轴最大 1307px，与 Header/Journey/Sticky 对齐；Sidebar 保持可见，页面不再横向摊薄或整体缩放。
- 1536×1024 与刷新：Sidebar、完整原问题、PICO、Terms、MeSH、Query、Limits/Ready 和唯一 Sticky 执行按钮均已实际查看。
- 旧策略新增“重新生成”操作，只返回入口并以旧问题预填，用户可补全问题后创建新策略；不会静默伪造 PICO。

真实证据：`workspace-real-flow-1536x1024.png`、`workspace-real-flow-2560x1259.png`、`workspace-real-flow-refresh-1536x1024.png`。
