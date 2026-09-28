import { createRouter, createWebHistory } from "vue-router";

import { features } from "../config/features";
import { routeMeta } from "./route-meta";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/research-chat",
      component: () => import("../views/ResearchChat/ResearchChatView.vue"),
      meta: {
        breadcrumb: ["统一科研对话"],
        feature: { id: "research-chat", label: "统一科研对话", path: "/research-chat",
          icon: "message-circle", group: "研究工作区", phase: "FE-04", status: "LIVE",
          showInNavigation: false, requiresContextRail: false, mobileSupport: true },
      },
    },
    {
      path: "/",
      component: () => import("../views/Home/HomeView.vue"),
      meta: routeMeta("/"),
    },
    {
      path: "/models",
      component: () => import("../views/ModelSettings/ModelSettingsView.vue"),
      meta: routeMeta("/models"),
    },
    {
      path: "/sources",
      component: () => import("../views/KnowledgeBase/KnowledgeBaseView.vue"),
      meta: routeMeta("/sources"),
    },
    {
      path: "/documents",
      component: () => import("../views/Documents/DocumentsView.vue"),
      meta: routeMeta("/documents"),
    },
    {
      path: "/papers",
      component: () => import("../views/PaperLibrary/PaperLibraryView.vue"),
      meta: routeMeta("/papers"),
    },
    {
      path: "/paper-center",
      component: () => import("../views/PaperCenter/PaperCenterView.vue"),
      meta: routeMeta("/paper-research", "/paper-center"),
    },
    {
      path: "/paper-research/:paperItemId?",
      component: () => import("../views/PaperReader/PaperReaderView.vue"),
      meta: routeMeta("/paper-research"),
    },
    {
      path: "/notes",
      component: () => import("../views/NoteLibrary/NoteLibraryView.vue"),
      meta: routeMeta("/notes"),
    },
    {
      path: "/documents/:id",
      component: () => import("../views/Documents/DocumentDetailView.vue"),
      meta: routeMeta("/documents", "/documents/detail"),
    },
    {
      path: "/literature-search",
      // 检索中心展示研究问题入口；完整策略工作台继续使用 /workspace，
      // 让入口页与策略编辑页各自保持单一职责。
      component: () => import("../views/LiteratureSearch/SearchEntryView.vue"),
      meta: routeMeta("/literature-search"),
      beforeEnter: (to) => {
        if (to.query.tab !== "history") return true;
        const query = { ...to.query };
        delete query.tab;
        return { path: "/literature-search/history", query, replace: true };
      },
    },
    {
      path: "/literature-search/start",
      component: () => import("../views/LiteratureSearch/SearchEntryView.vue"),
      meta: routeMeta("/literature-search"),
    },
    {
      path: "/literature-search/workspace",
      component: () =>
        import("../views/LiteratureSearch/LiteratureSearchView.vue"),
      meta: routeMeta("/literature-search", "/literature-search/workspace"),
      beforeEnter: (to) => {
        const strategyId = Number(to.query.strategy_id);
        if (Number.isInteger(strategyId) && strategyId > 0) return true;
        const query = { ...to.query };
        delete query.strategy_id;
        return { path: "/literature-search", query, replace: true };
      },
    },
    {
      path: "/recommendations",
      component: () =>
        import("../views/Recommendations/RecommendationsView.vue"),
      meta: routeMeta("/recommendations"),
    },
    {
      path: "/literature-search/history",
      component: () => import("../views/LiteratureSearch/History.vue"),
      meta: routeMeta("/literature-search/history"),
    },
    {
      path: "/literature-search/results",
      component: () => import("../views/LiteratureSearch/ResultsIndexView.vue"),
      meta: routeMeta("/literature-search/results"),
    },
    {
      path: "/literature-search/results/:id",
      component: () => import("../views/LiteratureSearch/ResultsView.vue"),
      meta: routeMeta("/literature-search/results"),
    },
    {
      path: "/feedback",
      component: () => import("../views/Feedback/FeedbackView.vue"),
      meta: routeMeta("/feedback"),
    },
    {
      path: "/comparisons",
      component: () => import("../views/Comparison/ComparisonView.vue"),
      meta: routeMeta("/comparisons"),
    },
    {
      path: "/evidence-matrix",
      component: () => import("../views/EvidenceMatrix/EvidenceMatrixView.vue"),
      meta: routeMeta("/evidence-matrix"),
    },
    {
      path: "/research-directions",
      component: () =>
        import("../views/ResearchDirections/ResearchDirectionsView.vue"),
      meta: routeMeta("/research-directions"),
    },
    {
      path: "/citation-check",
      component: () => import("../views/CitationCheck/CitationCheckView.vue"),
      meta: routeMeta("/citation-check"),
    },
    {
      path: "/presentations",
      component: () => import("../views/Presentations/PresentationsView.vue"),
      meta: routeMeta("/presentations"),
    },
    {
      path: "/presentations/:id",
      component: () =>
        import("../views/Presentations/PresentationEditorView.vue"),
      meta: routeMeta("/presentations"),
    },
    {
      path: "/writing",
      component: () => import("../views/Writing/WritingView.vue"),
      meta: routeMeta("/writing"),
    },
    {
      path: "/writing/:id",
      component: () => import("../views/Writing/WritingEditorView.vue"),
      meta: routeMeta("/writing"),
    },
    {
      path: "/tasks",
      component: () => import("../views/Tasks/TasksView.vue"),
      meta: routeMeta("/tasks"),
    },
    {
      path: "/agent",
      component: () => import("../views/Agent/AgentView.vue"),
      meta: routeMeta("/agent"),
    },
    {
      path: "/evaluation",
      component: () => import("../views/Evaluation/EvaluationView.vue"),
      meta: routeMeta("/evaluation"),
    },
    ...features
      .filter(
        (feature) =>
          ![
            "/",
            "/models",
            "/sources",
            "/documents",
            "/paper-research",
            "/notes",
            "/literature-search",
            "/recommendations",
            "/feedback",
            "/comparisons",
            "/evidence-matrix",
            "/research-directions",
            "/citation-check",
            "/presentations",
            "/writing",
            "/tasks",
            "/agent",
            "/evaluation",
          ].includes(feature.path),
      )
      .map((feature) => ({
        path: feature.path,
        component: () => import("../views/System/FeatureUnavailableView.vue"),
        meta: { feature },
      })),
  ],
});
