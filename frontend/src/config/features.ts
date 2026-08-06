import type { FeatureDefinition } from "../types/feature";

export const features: FeatureDefinition[] = [
  { id: "workbench", label: "工作台", path: "/", icon: "⌂", group: "研究空间", phase: "FE-02", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "analysis", label: "论文分析", path: "/analysis", icon: "◈", group: "研究空间", phase: "FE-03", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "chat", label: "证据问答", path: "/chat", icon: "◌", group: "研究空间", phase: "FE-03", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "sources", label: "知识库", path: "/sources", icon: "◫", group: "知识资产", phase: "FE-02", status: "LIVE", showInNavigation: true, requiresContextRail: true, mobileSupport: true },
  { id: "documents", label: "文档库", path: "/documents", icon: "▤", group: "知识资产", phase: "FE-02", status: "LIVE", showInNavigation: true, requiresContextRail: true, mobileSupport: true },
  { id: "literature", label: "文献检索", path: "/literature-search", icon: "⌕", group: "知识资产", phase: "FE-04", status: "LIVE", showInNavigation: true, requiresContextRail: true, mobileSupport: true },
  { id: "comparison", label: "多论文比较", path: "/comparisons", icon: "≋", group: "知识资产", phase: "FE-05", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "matrix", label: "证据矩阵", path: "/evidence-matrix", icon: "⊞", group: "知识资产", phase: "FE-05", status: "MOCK", showInNavigation: false, requiresContextRail: false, mobileSupport: false },
  { id: "reading-plan", label: "收藏与阅读计划", path: "/reading-plan", icon: "◇", group: "知识资产", phase: "FE-05", status: "UNAVAILABLE", showInNavigation: false, requiresContextRail: false, mobileSupport: false },
  { id: "directions", label: "研究方向", path: "/research-directions", icon: "↗", group: "科研产出", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "writing", label: "写作与汇报", path: "/writing", icon: "✎", group: "科研产出", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "report", label: "组会汇报", path: "/presentations", icon: "▥", group: "科研产出", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "citation-check", label: "引用核验", path: "/citation-check", icon: "✓", group: "科研产出", phase: "FE-06", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "agent", label: "Agent 实验室", path: "/agent", icon: "◉", group: "智能工具", phase: "FE-07", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "evaluation", label: "评测中心", path: "/evaluation", icon: "✓", group: "智能工具", phase: "FE-07", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "tasks", label: "任务中心", path: "/tasks", icon: "◷", group: "底部", phase: "FE-07", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "feedback", label: "反馈与帮助", path: "/feedback", icon: "?", group: "底部", phase: "FE-01", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "models", label: "设置", path: "/models", icon: "⚙", group: "底部", phase: "FE-07", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
];

export const featureByPath = (path: string) => features.find((feature) => feature.path === path);
