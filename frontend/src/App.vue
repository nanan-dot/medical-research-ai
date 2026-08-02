<script setup lang="ts">
import { shallowRef } from "vue";

import KnowledgeBaseView from "./views/KnowledgeBase/KnowledgeBaseView.vue";
import DocumentsView from "./views/Documents/DocumentsView.vue";
import PaperAnalysisView from "./views/PaperAnalysis/PaperAnalysisView.vue";

const activeView = shallowRef<"sources" | "documents" | "analysis">("documents");
</script>

<template>
  <nav class="app-nav" aria-label="主导航">
    <button :class="{ active: activeView === 'documents' }" @click="activeView = 'documents'">文档状态</button>
    <button :class="{ active: activeView === 'sources' }" @click="activeView = 'sources'">知识源</button>
    <button :class="{ active: activeView === 'analysis' }" @click="activeView = 'analysis'">论文分析</button>
  </nav>
  <DocumentsView v-if="activeView === 'documents'" />
  <KnowledgeBaseView v-else-if="activeView === 'sources'" />
  <PaperAnalysisView v-else />
</template>

<style scoped>
.app-nav { position: sticky; top: 0; z-index: 10; display: flex; justify-content: center; gap: 0.4rem; padding: 0.75rem; background: rgba(239, 244, 240, 0.88); backdrop-filter: blur(12px); }
.app-nav button { border: 0; border-radius: 99px; padding: 0.55rem 0.9rem; background: transparent; color: #53686b; font-weight: 700; }
.app-nav button.active { background: #173f3c; color: #fff; }
</style>
