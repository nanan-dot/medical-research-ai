<script setup lang="ts">
import { computed, shallowRef } from "vue";

import type { DocumentRecord } from "../../api/documents";
import type { PaperAnalysis } from "../../api/paperAnalysis";
import EvidenceRail from "./EvidenceRail.vue";
import InsightBlock from "./InsightBlock.vue";
import PaperAnalysisContextBar from "./PaperAnalysisContextBar.vue";
import PaperHeader from "./PaperHeader.vue";
import PaperMetadataBar from "./PaperMetadataBar.vue";
import ResearchBrief from "./ResearchBrief.vue";
import {
  overallConfidence,
  toEvidenceCards,
  toInsightBlocks,
  toSourceKinds,
  type ConfidenceLevel,
  type InsightBlockModel,
} from "./paperModel";

const props = defineProps<{
  document: DocumentRecord | null;
  analysis: PaperAnalysis | null;
  loading: boolean;
  error: string | null;
  canAnalyze: boolean;
  canAnnotate: boolean;
}>();

const emit = defineEmits<{
  create: [];
  regenerate: [];
  openChat: [];
  openAnnotation: [];
}>();

const railOpen = shallowRef(false);
const evidenceCards = computed(() => toEvidenceCards(props.analysis?.sources ?? []));
const blocks = computed<InsightBlockModel[]>(() =>
  props.analysis?.structured_result ? toInsightBlocks(props.analysis.structured_result, evidenceCards.value) : [],
);
const sourceKinds = computed(() => toSourceKinds(props.analysis?.structured_result ?? null));
const confidence = computed<ConfidenceLevel>(() =>
  props.analysis?.structured_result ? overallConfidence(Object.values(props.analysis.structured_result)) : "needs-verification",
);
const studyType = computed(() => props.analysis?.structured_result?.study_type?.value || null);
const sampleSize = computed(() => props.analysis?.structured_result?.sample_size?.value || null);
const documentLabel = computed(() => props.document?.original_filename || props.document?.file_path || "未选择论文");

function handleJump(localIndex: number): void {
  railOpen.value = true;
  window.requestAnimationFrame(() => {
    document.querySelector<HTMLElement>(`[aria-label="证据卡 ${localIndex + 1}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
}

function jumpToBlock(field: string): void {
  window.document.getElementById(`analysis-${field}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function goBack(): void {
  window.history.back();
}
</script>

<template>
  <section class="analysis-section" aria-labelledby="paper-analysis-title">
    <header class="section-header"><p class="eyebrow">STRUCTURED PAPER REPORT</p><h2 id="paper-analysis-title" class="section-title">论文分析</h2><p class="section-description">查看当前论文已保存的结构化分析；若尚未生成，可从这里创建分析。</p></header>
    <p v-if="!props.document" class="state-copy">请先选择一篇论文，系统会读取该论文最近一次已保存的分析。</p>
    <template v-else-if="props.loading"><p class="state-copy">正在读取或生成论文分析…</p></template>
    <template v-else-if="props.analysis">
      <PaperAnalysisContextBar :analysis="props.analysis" :title="documentLabel" />
      <p v-if="props.error" class="error" role="alert">{{ props.error }}</p>
      <div class="report-layout">
        <nav class="report-outline" aria-label="分析目录"><strong>分析目录</strong><button v-for="block in blocks" :key="block.field" type="button" @click="jumpToBlock(block.field)">{{ block.label }}</button><p v-if="blocks.length === 0">结构化结果为空</p></nav>
        <article class="report"><PaperHeader :analysis="props.analysis" :busy="props.loading" @back="goBack" @regenerate="emit('regenerate')" /><ResearchBrief :title="documentLabel" :author="null" :analysis="props.analysis" :confidence="confidence" /><div v-if="blocks.length === 0" class="empty-report">结构化分析结果未提供。请查看当前状态，或在完成后重新生成。</div><div v-else class="block-list"><div v-for="block in blocks" :id="`analysis-${block.field}`" :key="block.field"><InsightBlock :block="block" @jump="handleJump" /></div></div><PaperMetadataBar :study-type="studyType" :sample-size="sampleSize" :evidence-count="props.analysis.sources.length" /><div class="next-actions"><button type="button" @click="emit('openChat')">进入单篇问答</button><button type="button" :disabled="!props.canAnnotate" @click="emit('openAnnotation')">打开原文批注</button><span v-if="!props.canAnnotate" class="unavailable">当前文档不是 PDF，无法打开原文批注。</span></div></article>
        <EvidenceRail class="evidence-rail" :cards="evidenceCards" :source-kinds="sourceKinds" @jump="handleJump" />
      </div>
    </template>
    <template v-else><p v-if="props.error" class="error" role="alert">{{ props.error }}</p><p class="state-copy">该论文尚无已保存的结构化分析。</p><button class="primary-action" type="button" :disabled="!props.canAnalyze" @click="emit('create')">开始分析</button><p v-if="!props.canAnalyze" class="unavailable">当前文档尚未完成解析和索引，暂不能发起论文分析。</p></template>
  </section>
</template>

<style scoped>
.analysis-section { display: grid; gap: .85rem; padding: 1.15rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); background: var(--surface); box-shadow: var(--shadow); }.section-header { display: grid; gap: .3rem; }.eyebrow { margin: 0; color: var(--color-primary); font-size: .7rem; font-weight: 900; letter-spacing: .1em; }.section-title { margin: 0; color: var(--text-primary); font-size: 1.18rem; }.section-description,.state-copy,.unavailable { margin: 0; color: var(--text-muted); font-size: .86rem; }.error { margin: 0; color: var(--color-danger); }.primary-action,.next-actions button { padding: .62rem .85rem; border: 1px solid var(--color-primary); border-radius: 8px; background: var(--color-primary); color: #fff; font: inherit; font-weight: 750; }.primary-action { justify-self: start; }.primary-action:disabled,.next-actions button:disabled { opacity: .55; cursor: not-allowed; }.report-layout { display: grid; grid-template-columns: 184px minmax(0, 1fr) minmax(230px, 27%); overflow: hidden; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); }.report-outline { display: grid; align-content: start; gap: 4px; padding: 12px; border-right: 1px solid var(--border-subtle); background: var(--surface-raised); font-size: .78rem; }.report-outline button { overflow: hidden; padding: 6px 4px; border: 0; background: transparent; color: var(--text-muted); font: inherit; text-align: left; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }.report-outline button:hover,.report-outline button:focus-visible { color: var(--color-primary); outline: none; }.report-outline p { color: var(--text-muted); }.report { display: grid; align-content: start; gap: .85rem; min-width: 0; padding: 1rem; background: var(--page-bg); }.evidence-rail { border-left: 1px solid var(--border-subtle); }.block-list { display: grid; gap: .75rem; }.empty-report { padding: .85rem; border: 1px dashed var(--border-strong); border-radius: 8px; color: var(--text-muted); }.next-actions { display: flex; flex-wrap: wrap; align-items: center; gap: .55rem; }.next-actions button + button { border-color: var(--border-strong); background: var(--paper); color: var(--text-primary); } @media (max-width: 960px) { .report-layout { grid-template-columns: 1fr; }.report-outline { border-right: 0; border-bottom: 1px solid var(--border-subtle); }.evidence-rail { border-top: 1px solid var(--border-subtle); border-left: 0; } }
</style>
