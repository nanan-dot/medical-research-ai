import { createRouter, createWebHistory } from "vue-router";

import HomeView from "../views/Home/HomeView.vue";
import KnowledgeBaseView from "../views/KnowledgeBase/KnowledgeBaseView.vue";
import DocumentsView from "../views/Documents/DocumentsView.vue";
import DocumentDetailView from "../views/Documents/DocumentDetailView.vue";
import LiteratureSearchView from "../views/LiteratureSearch/LiteratureSearchView.vue";
import PaperAnalysisView from "../views/PaperAnalysis/PaperAnalysisView.vue";
import ChatView from "../views/Chat/ChatView.vue";
import ModelSettingsView from "../views/ModelSettings/ModelSettingsView.vue";
import FeedbackView from "../views/Feedback/FeedbackView.vue";
import ComparisonView from "../views/Comparison/ComparisonView.vue";
import EvidenceMatrixView from "../views/EvidenceMatrix/EvidenceMatrixView.vue";
import ResearchDirectionsView from "../views/ResearchDirections/ResearchDirectionsView.vue";
import PresentationsView from "../views/Presentations/PresentationsView.vue";
import PresentationEditorView from "../views/Presentations/PresentationEditorView.vue";
import WritingView from "../views/Writing/WritingView.vue";
import WritingEditorView from "../views/Writing/WritingEditorView.vue";
import FeatureUnavailableView from "../views/System/FeatureUnavailableView.vue";
import { features } from "../config/features";
import { routeMeta } from "./route-meta";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: HomeView, meta: routeMeta("/") },
    { path: "/models", component: ModelSettingsView, meta: routeMeta("/models") },
    { path: "/sources", component: KnowledgeBaseView, meta: routeMeta("/sources") },
    { path: "/documents", component: DocumentsView, meta: routeMeta("/documents") },
    { path: "/documents/:id", component: DocumentDetailView, meta: routeMeta("/documents") },
    { path: "/literature-search", component: LiteratureSearchView, meta: routeMeta("/literature-search") },
    { path: "/analysis", component: PaperAnalysisView, meta: routeMeta("/analysis") },
    { path: "/chat", component: ChatView, meta: routeMeta("/chat") },
    { path: "/feedback", component: FeedbackView, meta: routeMeta("/feedback") },
    { path: "/comparisons", component: ComparisonView, meta: routeMeta("/comparisons") },
    { path: "/evidence-matrix", component: EvidenceMatrixView, meta: routeMeta("/evidence-matrix") },
    { path: "/research-directions", component: ResearchDirectionsView, meta: routeMeta("/research-directions") },
    { path: "/presentations", component: PresentationsView, meta: routeMeta("/presentations") },
    { path: "/presentations/:id", component: PresentationEditorView, meta: routeMeta("/presentations") },
    { path: "/writing", component: WritingView, meta: routeMeta("/writing") },
    { path: "/writing/:id", component: WritingEditorView, meta: routeMeta("/writing") },
    ...features.filter((feature) => !["/", "/models", "/sources", "/documents", "/literature-search", "/analysis", "/chat", "/feedback", "/comparisons", "/evidence-matrix", "/research-directions", "/presentations", "/writing"].includes(feature.path)).map((feature) => ({ path: feature.path, component: FeatureUnavailableView, meta: { feature } })),
  ],
});
