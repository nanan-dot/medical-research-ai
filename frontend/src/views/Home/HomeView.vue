<script setup lang="ts">
import { inject, onMounted, shallowRef } from "vue";
import { documentsApi, type DocumentRecord } from "../../api/documents";
import ResearchHero from "../../components/home/ResearchHero.vue";
import ResearchSearch from "../../components/home/ResearchSearch.vue";
import FeatureEntry from "../../components/home/FeatureEntry.vue";
import RecentResearchList from "../../components/home/RecentResearchList.vue";
import TaskProgressPanel from "../../components/home/TaskProgressPanel.vue";
import KnowledgeOverview from "../../components/home/KnowledgeOverview.vue";

const openSearch = inject<() => void>("openSearch", () => {});
const documents = shallowRef<DocumentRecord[]>([]);
const documentsLoading = shallowRef(true);
const documentsError = shallowRef("");

onMounted(async () => {
  try {
    documents.value = (await documentsApi.list({ parseStatus: "", indexStatus: "" }, 0, 20)).items;
  } catch (cause) {
    documentsError.value = cause instanceof Error ? cause.message : "无法读取最近研究";
  } finally {
    documentsLoading.value = false;
  }
});

const capabilities = [
  { label: "论文分析", description: "深入解析医学论文", path: "/analysis", icon: "◈" },
  { label: "证据问答", description: "基于证据链回答", path: "/chat", icon: "◌" },
  { label: "文献检索", description: "构建医学检索任务", path: "/literature-search", icon: "⌕" },
  { label: "多论文比较", description: "发现研究差异", path: "/comparisons", icon: "≋" },
  { label: "知识库", description: "管理科研资产", path: "/sources", icon: "◫" },
  { label: "组会汇报", description: "自动生成材料", path: "/presentations", icon: "▥" },
];
</script>
<template>
  <main class="home">
    <ResearchHero title="LIGHT RESEARCH WORKSPACE" description="管理知识源、追踪论文解析与索引，并在真实状态上继续你的研究。检索、分析、问答等能力均已如实标注接入状态。" />
    <ResearchSearch @open="openSearch" />
    <h2 class="section-title">研究能力入口</h2>
    <FeatureEntry :items="capabilities" />
    <div class="columns">
      <RecentResearchList :items="documents" :loading="documentsLoading" :error="documentsError" />
      <TaskProgressPanel />
      <KnowledgeOverview />
    </div>
    <p class="phase-note">本阶段仅重构工作台视觉与信息架构；所有状态均来自真实接口或如实标注，不伪造论文与任务进度。</p>
  </main>
</template>
<style scoped>
.home{max-width:1180px;margin:auto;padding:1.6rem 1.6rem 2.4rem;display:grid;gap:1.5rem}.section-title{margin:0;color:var(--text-primary);font-size:1rem}.columns{display:grid;grid-template-columns:35fr 35fr 30fr;gap:1.4rem;align-items:start}.columns>section{min-width:0}.phase-note{margin:0;color:var(--text-faint);font-size:.78rem}@media(max-width:1100px){.columns{grid-template-columns:1fr 1fr}.columns>section:last-child{grid-column:1/-1}}@media(max-width:760px){.columns{grid-template-columns:1fr}.columns>section:last-child{grid-column:auto}.home{padding:1rem}}
</style>
