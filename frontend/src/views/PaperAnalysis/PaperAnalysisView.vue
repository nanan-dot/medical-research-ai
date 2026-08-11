<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import IndexedPaperPicker from "../../components/paper/IndexedPaperPicker.vue";
import PaperAnalysisSection from "../../components/paper/PaperAnalysisSection.vue";
import PendingConfirmationList from "../../components/paper/PendingConfirmationList.vue";
import PaperEvidenceWorkspace from "../../components/paper/PaperEvidenceWorkspace.vue";
import ResearchOverviewStreams from "../../components/paper/ResearchOverviewStreams.vue";
import { usePaperResearchWorkflow } from "../../composables/usePaperResearchWorkflow";
import { useResearchOverview } from "../../composables/useResearchOverview";

type ResearchTab = "overview" | "reading" | "evidence";
const route = useRoute(); const router = useRouter(); const workflow = usePaperResearchWorkflow(); const overview = useResearchOverview();
const tab = computed<ResearchTab>(() => route.query.tab === "reading" ? "reading" : route.query.tab === "evidence" ? "evidence" : "overview");
const hasEvidenceScope = computed(() => Boolean(
  workflow.selectedDocument.value
  || route.query.documentId
  || route.query.conversationId
  || route.query.analysisId,
));
function setTab(next: ResearchTab): void { void router.replace({ query: { ...route.query, tab: next === "overview" ? undefined : next } }); }
function openReading(documentId: number, analysisId?: number): void { void router.push({ path: "/analysis", query: { documentId: String(documentId), tab: "reading", ...(analysisId ? { analysisId: String(analysisId) } : {}) } }); }
function openChat(conversationId?: number, documentId?: number | null): void { void router.push({ path: "/analysis", query: { tab: "evidence", ...(documentId ? { documentId: String(documentId) } : {}), ...(conversationId ? { conversationId: String(conversationId) } : {}) } }); }
</script>
<template>
 <main class="research-page" aria-label="论文研究"><header class="page-header"><h1>论文研究</h1><p>读懂、核对并沉淀一篇或一组论文的证据。</p></header>
  <nav class="tabs" aria-label="论文研究局部标签"><button type="button" :class="{ active: tab === 'overview' }" :aria-current="tab === 'overview' ? 'page' : undefined" @click="setTab('overview')">研究概览</button><button type="button" :class="{ active: tab === 'reading' }" @click="setTab('reading')">单篇精读</button><button type="button" :class="{ active: tab === 'evidence' }" @click="setTab('evidence')">证据问答</button></nav>
  <section v-if="tab === 'overview'" class="overview-layout"><div class="main-column"><IndexedPaperPicker :papers="overview.papers.value.items" :loading="overview.papersLoading.value" :error="overview.papersError.value" @search="overview.loadPapers" @select="openReading($event.document_id)" /><ResearchOverviewStreams :overview="overview.overview.value" :loading="overview.overviewLoading.value" :error="overview.overviewError.value" @read="openReading" @chat="openChat" /></div><PendingConfirmationList :items="overview.overview.value.pending_confirmations" :loading="overview.overviewLoading.value" :error="overview.overviewError.value" @open="openReading" /></section>
  <section v-else-if="tab === 'reading'" class="detail"><p v-if="!workflow.selectedDocument.value" class="empty">请先在研究概览选择一篇已索引论文。</p><PaperAnalysisSection v-else :document="workflow.selectedDocument.value" :analysis="workflow.analysis.value" :loading="workflow.analysisLoading.value" :error="workflow.analysisError.value" :can-analyze="workflow.canAnalyze.value" :can-annotate="workflow.canAnnotate.value" @create="workflow.createAnalysis" @regenerate="workflow.regenerateAnalysis" @open-chat="openChat(undefined, workflow.selectedDocument.value.id)" @open-annotation="openReading(workflow.selectedDocument.value.id)" /></section>
  <section v-else-if="!hasEvidenceScope" class="unavailable"><h2>证据问答需要论文范围</h2><p>请先选择论文或证据范围，再开始证据问答。</p><button type="button" @click="setTab('overview')">前往研究概览</button></section>
  <PaperEvidenceWorkspace v-else :document="workflow.selectedDocument.value" :can-create="workflow.canAnalyze.value" @change-paper="setTab('overview')" @return-overview="setTab('overview')" />
 </main>
</template>
<style scoped>
.research-page{width:min(100% - 3rem,1280px);min-height:calc(100vh - 65px);margin:0 auto;padding:1.7rem 0 2.5rem}.page-header h1{margin:0;color:var(--text-primary);font-size:clamp(1.75rem,2.5vw,2rem);font-weight:700;line-height:1.2}.page-header p{margin:.35rem 0 1rem;color:var(--text-muted);font-size:.94rem}.tabs{display:flex;gap:1.25rem;margin-bottom:1.25rem;border-bottom:1px solid var(--border-subtle)}.tabs button{padding:.6rem 0;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--text-muted);font:inherit;cursor:pointer}.tabs button.active{border-color:var(--color-primary);color:var(--color-primary);font-weight:700}.overview-layout{display:grid;grid-template-columns:minmax(0,3fr) minmax(300px,2fr);gap:1.25rem;align-items:start}.main-column{display:grid;gap:1.25rem}.detail,.unavailable{padding:1.1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--surface)}.empty,.unavailable p{color:var(--text-muted)}.unavailable h2{margin:0;font-size:1.25rem}.unavailable button{border:1px solid var(--color-primary);border-radius:7px;padding:.6rem .8rem;background:var(--color-primary);color:#fff;font:inherit;font-weight:700}.unavailable button:disabled{opacity:.5;cursor:not-allowed}@media(max-width:1279px){.overview-layout{grid-template-columns:1fr}.overview-layout>:last-child{order:2}}@media(max-width:640px){.research-page{width:min(100% - 2rem,1280px);padding-top:1rem}.tabs{overflow-x:auto}.tabs button{flex:none;white-space:nowrap}}
</style>
