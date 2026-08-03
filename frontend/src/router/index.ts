import { createRouter, createWebHistory } from "vue-router";

import { features } from "../config/features";
import { routeMeta } from "./route-meta";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("../views/Home/HomeView.vue"), meta: routeMeta("/") },
    { path: "/models", component: () => import("../views/ModelSettings/ModelSettingsView.vue"), meta: routeMeta("/models") },
    { path: "/sources", component: () => import("../views/KnowledgeBase/KnowledgeBaseView.vue"), meta: routeMeta("/sources") },
    { path: "/documents", component: () => import("../views/Documents/DocumentsView.vue"), meta: routeMeta("/documents") },
    { path: "/documents/:id", component: () => import("../views/Documents/DocumentDetailView.vue"), meta: routeMeta("/documents") },
    { path: "/literature-search", component: () => import("../views/LiteratureSearch/LiteratureSearchView.vue"), meta: routeMeta("/literature-search") },
    { path: "/analysis", component: () => import("../views/PaperAnalysis/PaperAnalysisView.vue"), meta: routeMeta("/analysis") },
    { path: "/chat", component: () => import("../views/Chat/ChatView.vue"), meta: routeMeta("/chat") },
    { path: "/feedback", component: () => import("../views/Feedback/FeedbackView.vue"), meta: routeMeta("/feedback") },
    { path: "/comparisons", component: () => import("../views/Comparison/ComparisonView.vue"), meta: routeMeta("/comparisons") },
    { path: "/evidence-matrix", component: () => import("../views/EvidenceMatrix/EvidenceMatrixView.vue"), meta: routeMeta("/evidence-matrix") },
    { path: "/research-directions", component: () => import("../views/ResearchDirections/ResearchDirectionsView.vue"), meta: routeMeta("/research-directions") },
    { path: "/presentations", component: () => import("../views/Presentations/PresentationsView.vue"), meta: routeMeta("/presentations") },
    { path: "/presentations/:id", component: () => import("../views/Presentations/PresentationEditorView.vue"), meta: routeMeta("/presentations") },
    { path: "/writing", component: () => import("../views/Writing/WritingView.vue"), meta: routeMeta("/writing") },
    { path: "/writing/:id", component: () => import("../views/Writing/WritingEditorView.vue"), meta: routeMeta("/writing") },
    { path: "/tasks", component: () => import("../views/Tasks/TasksView.vue"), meta: routeMeta("/tasks") },
    { path: "/agent", component: () => import("../views/Agent/AgentView.vue"), meta: routeMeta("/agent") },
    { path: "/evaluation", component: () => import("../views/Evaluation/EvaluationView.vue"), meta: routeMeta("/evaluation") },
    ...features.filter((feature) => !["/", "/models", "/sources", "/documents", "/literature-search", "/analysis", "/chat", "/feedback", "/comparisons", "/evidence-matrix", "/research-directions", "/presentations", "/writing", "/tasks", "/agent", "/evaluation"].includes(feature.path)).map((feature) => ({ path: feature.path, component: () => import("../views/System/FeatureUnavailableView.vue"), meta: { feature } })),
  ],
});
