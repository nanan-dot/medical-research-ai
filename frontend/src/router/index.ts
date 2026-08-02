import { createRouter, createWebHistory } from "vue-router";

import HomeView from "../views/Home/HomeView.vue";
import KnowledgeBaseView from "../views/KnowledgeBase/KnowledgeBaseView.vue";
import DocumentsView from "../views/Documents/DocumentsView.vue";
import LiteratureSearchView from "../views/LiteratureSearch/LiteratureSearchView.vue";
import PaperAnalysisView from "../views/PaperAnalysis/PaperAnalysisView.vue";
import ChatView from "../views/Chat/ChatView.vue";
import ModelSettingsView from "../views/ModelSettings/ModelSettingsView.vue";
import FeedbackView from "../views/Feedback/FeedbackView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: HomeView },
    { path: "/models", component: ModelSettingsView },
    { path: "/sources", component: KnowledgeBaseView },
    { path: "/documents", component: DocumentsView },
    { path: "/literature-search", component: LiteratureSearchView },
    { path: "/analysis", component: PaperAnalysisView },
    { path: "/chat", component: ChatView },
    { path: "/feedback", component: FeedbackView },
  ],
});
