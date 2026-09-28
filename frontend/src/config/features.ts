import type { FeatureDefinition } from "../types/feature";

// 素问 · 医学循证研究平台 — 主导航与底部入口。
// 保留仍受支持的功能路由与状态，并按研究空间分组。
// 底部：后台任务、设置。未列入主导航的功能仍可通过路由直接访问。
export const features: FeatureDefinition[] = [
  { id: "workbench", label: "工作台", path: "/", icon: "⌂", group: "研究空间", phase: "FE-02", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "literature", label: "文献检索", path: "/literature-search", icon: "⌕", group: "研究空间", phase: "FE-04", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "documents", label: "研究资源", path: "/documents", icon: "▤", group: "研究空间", phase: "FE-02", status: "LIVE", showInNavigation: true, requiresContextRail: true, mobileSupport: true },
  { id: "papers", label: "论文库", path: "/papers", icon: "▤", group: "研究空间", phase: "FE-02", status: "LIVE", showInNavigation: false, requiresContextRail: false, mobileSupport: true },
  { id: "paper-research", label: "论文研究", path: "/paper-research", icon: "▤", group: "研究空间", phase: "FE-07", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "notes", label: "笔记库", path: "/notes", icon: "▥", group: "研究空间", phase: "FE-07", status: "LIVE", showInNavigation: false, requiresContextRail: false, mobileSupport: true },
  { id: "comparison", label: "多论文证据", path: "/comparisons", icon: "≋", group: "研究空间", phase: "FE-05", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "directions", label: "研究设计", path: "/research-directions", icon: "↗", group: "研究空间", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "writing", label: "写作与汇报", path: "/writing", icon: "✎", group: "研究空间", phase: "FE-06", status: "MOCK", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "tasks", label: "后台任务", path: "/tasks", icon: "◷", group: "底部", phase: "FE-07", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  { id: "models", label: "设置", path: "/models", icon: "⚙", group: "底部", phase: "FE-07", status: "LIVE", showInNavigation: true, requiresContextRail: false, mobileSupport: true },
  // 以下功能保留路由可达，但不进入主导航（可通过工作台快捷动作或直接 URL 访问）。
  { id: "sources", label: "知识库", path: "/sources", icon: "◫", group: "研究空间", phase: "FE-02", status: "LIVE", showInNavigation: false, requiresContextRail: true, mobileSupport: true },
  { id: "recommendations", label: "文献推荐", path: "/recommendations", icon: "✦", group: "研究空间", phase: "R4-WP05", status: "LIVE", showInNavigation: false, requiresContextRail: true, mobileSupport: true },
  { id: "matrix", label: "证据矩阵", path: "/evidence-matrix", icon: "⊞", group: "研究空间", phase: "FE-05", status: "MOCK", showInNavigation: false, requiresContextRail: false, mobileSupport: false },
  { id: "report", label: "组会汇报", path: "/presentations", icon: "▥", group: "研究空间", phase: "FE-06", status: "MOCK", showInNavigation: false, requiresContextRail: false, mobileSupport: true },
  { id: "citation-check", label: "引用核验", path: "/citation-check", icon: "✓", group: "研究空间", phase: "FE-06", status: "LIVE", showInNavigation: false, requiresContextRail: false, mobileSupport: true },
  { id: "agent", label: "Agent 实验室", path: "/agent", icon: "◉", group: "研究空间", phase: "FE-07", status: "MOCK", showInNavigation: false, requiresContextRail: false, mobileSupport: true },
  { id: "evaluation", label: "评测中心", path: "/evaluation", icon: "✓", group: "研究空间", phase: "FE-07", status: "MOCK", showInNavigation: false, requiresContextRail: false, mobileSupport: true },
  { id: "feedback", label: "反馈与帮助", path: "/feedback", icon: "?", group: "底部", phase: "FE-01", status: "LIVE", showInNavigation: false, requiresContextRail: false, mobileSupport: true },
];

export const featureByPath = (path: string) => features.find((feature) => feature.path === path);
