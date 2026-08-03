import type { FeatureDefinition } from "../types/feature";

export const features: FeatureDefinition[] = [
  { id: "workbench", label: "工作台", path: "/", icon: "⌂", group: "", phase: "FE-02", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "sources", label: "知识源", path: "/sources", icon: "◫", group: "论文与知识", phase: "FE-02", status: "LIVE", showInNavigation: true, requiresContextRail: true, mobileSupport: true },
  { id: "documents", label: "文档库", path: "/documents", icon: "▤", group: "论文与知识", phase: "FE-02", status: "LIVE", showInNavigation: true, requiresContextRail: true, mobileSupport: true },
  { id: "analysis", label: "论文分析", path: "/analysis", icon: "◈", group: "论文与知识", phase: "FE-03", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "chat", label: "证据问答", path: "/chat", icon: "◌", group: "论文与知识", phase: "FE-03", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "literature", label: "文献检索", path: "/literature-search", icon: "⌕", group: "文献研究", phase: "FE-04", status: "LIVE", showInNavigation: true, requiresContextRail: true, mobileSupport: true },
  { id: "reading-plan", label: "收藏与阅读计划", path: "/reading-plan", icon: "◇", group: "文献研究", phase: "FE-05", status: "UNAVAILABLE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "comparison", label: "多论文比对", path: "/comparisons", icon: "≋", group: "文献研究", phase: "FE-05", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "matrix", label: "证据矩阵", path: "/evidence-matrix", icon: "⊞", group: "文献研究", phase: "FE-05", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "directions", label: "研究方向", path: "/research-directions", icon: "↗", group: "研究与表达", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "report", label: "组会汇报", path: "/presentations", icon: "▥", group: "研究与表达", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "writing", label: "写作项目", path: "/writing", icon: "✎", group: "研究与表达", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "citation-check", label: "引用核验", path: "/citation-check", icon: "✓", group: "研究与表达", phase: "FE-06", status: "UNAVAILABLE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "agent", label: "Agent 实验室", path: "/agent", icon: "◉", group: "高级工具", phase: "FE-07", status: "UNAVAILABLE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "evaluation", label: "质量评测", path: "/evaluation", icon: "✓", group: "高级工具", phase: "FE-07", status: "UNAVAILABLE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "tasks", label: "任务中心", path: "/tasks", icon: "◷", group: "底部", phase: "FE-07", status: "UNAVAILABLE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "feedback", label: "反馈与帮助", path: "/feedback", icon: "?", group: "底部", phase: "FE-01", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "models", label: "设置", path: "/models", icon: "⚙", group: "底部", phase: "FE-07", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
];

export const featureByPath = (path: string) => features.find((feature) => feature.path === path);
