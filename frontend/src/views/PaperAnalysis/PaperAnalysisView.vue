<script setup lang="ts">
import { computed, shallowRef } from "vue";
import { paperAnalysisApi, type PaperAnalysis } from "../../api/paperAnalysis";
import EvidenceRail from "../../components/paper/EvidenceRail.vue";
import InsightBlock from "../../components/paper/InsightBlock.vue";
import PaperAnalysisContextBar from "../../components/paper/PaperAnalysisContextBar.vue";
import PaperHeader from "../../components/paper/PaperHeader.vue";
import PaperMetadataBar from "../../components/paper/PaperMetadataBar.vue";
import PaperOutline from "../../components/paper/PaperOutline.vue";
import ResearchBrief from "../../components/paper/ResearchBrief.vue";
import {
  overallConfidence,
  toEvidenceCards,
  toInsightBlocks,
  toSourceKinds,
  type ConfidenceLevel,
  type InsightBlockModel,
} from "../../components/paper/paperModel";

const documentId = shallowRef<number | null>(null);
const analysis = shallowRef<PaperAnalysis | null>(null);
const loading = shallowRef(false);
const error = shallowRef<string | null>(null);
const railOpen = shallowRef(false);

const evidenceCards = computed(() => toEvidenceCards(analysis.value?.sources ?? []));
const blocks = computed<InsightBlockModel[]>(() =>
  analysis.value?.structured_result ? toInsightBlocks(analysis.value.structured_result, evidenceCards.value) : [],
);
const sourceKinds = computed(() => toSourceKinds(analysis.value?.structured_result ?? null));
const confidence = computed<ConfidenceLevel>(() =>
  analysis.value?.structured_result
    ? overallConfidence(Object.values(analysis.value.structured_result))
    : "needs-verification",
);
const studyType = computed<string | null>(() => analysis.value?.structured_result?.study_type?.value || null);
const sampleSize = computed<string | null>(() => analysis.value?.structured_result?.sample_size?.value || null);

/** basic_information 是现有接口唯一可用的标题/作者承载字段，缺失时不猜测论文元数据。 */
const title = computed<string | null>(() => {
  const firstLine = analysis.value?.structured_result?.basic_information?.value.split("\n")[0]?.trim();
  return firstLine || null;
});
const author = computed<string | null>(() => {
  const lines = analysis.value?.structured_result?.basic_information?.value.split("\n") ?? [];
  const authorLine = lines.slice(1).join("\n");
  return authorLine.split(/[；;]/)[0]?.trim() || null;
});

/**
 * 大纲只启用能够落到当前结构化报告中真实分析块的项目。
 * “原文证据”同样只在 structured_result 明确返回对应字段时允许跳转。
 */
const SECTION_TO_BLOCK: Readonly<Record<string, readonly string[]>> = {
  abstract: ["一句话结论"],
  introduction: ["研究背景", "科学问题"],
  methods: ["研究设计", "对象和样本", "样本量", "干预或暴露", "对照", "统计方法"],
  results: ["主要结局", "主要结果"],
  discussion: ["创新", "局限", "下一步阅读"],
  references: ["原文证据"],
};
const availableOutlineSections = computed(() =>
  Object.entries(SECTION_TO_BLOCK)
    .filter(([, labels]) => blocks.value.some((block) => labels.includes(block.label)))
    .map(([sectionKey]) => sectionKey),
);

async function createAnalysis(): Promise<void> {
  if (!documentId.value) return;
  loading.value = true;
  error.value = null;
  try {
    analysis.value = await paperAnalysisApi.create(documentId.value);
    railOpen.value = false;
  } catch (cause) {
    console.warn("创建论文分析失败", cause);
    error.value = cause instanceof Error ? cause.message : "分析请求失败";
  } finally {
    loading.value = false;
  }
}

async function regenerate(): Promise<void> {
  if (!analysis.value) return;
  loading.value = true;
  error.value = null;
  try {
    analysis.value = await paperAnalysisApi.regenerate(analysis.value.id);
    railOpen.value = false;
  } catch (cause) {
    console.warn("重新生成论文分析失败", cause);
    error.value = cause instanceof Error ? cause.message : "重新生成失败";
  } finally {
    loading.value = false;
  }
}

function goBack(): void {
  window.history.back();
}

function handleJump(localIndex: number): void {
  railOpen.value = true;
  const scrollToEvidence = () => {
    document.querySelector<HTMLElement>(`[aria-label="证据卡 ${localIndex + 1}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  window.requestAnimationFrame(scrollToEvidence);
}

function scrollToLabel(sectionKey: string): void {
  const labels = SECTION_TO_BLOCK[sectionKey] ?? [];
  const heading = [...document.querySelectorAll<HTMLElement>(".analysis-block-title")]
    .find((node) => labels.includes(node.textContent?.trim() ?? ""));
  heading?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function toggleRail(): void {
  railOpen.value = !railOpen.value;
}
</script>

<template>
  <main class="analysis-page" aria-label="论文分析">
    <header class="page-header">
      <p class="eyebrow">PAPER RESEARCH · SINGLE-PAPER ANALYSIS</p>
      <h1 class="page-title">论文分析</h1>
      <p class="page-description">将当前已索引论文提取为可核对的研究信息；模型推断不会冒充原文事实。</p>
    </header>

    <nav class="analysis-tab" aria-label="论文研究二级导航">
      <span class="analysis-tab-current">论文分析</span>
    </nav>

    <section v-if="!analysis" class="empty-panel">
      <h2 class="empty-title">从已索引文档开始分析</h2>
      <p class="empty-copy">输入已索引文档 ID 后生成结构化报告；没有来源支撑的内容会保留“待核对”状态。</p>
      <form class="start-form" @submit.prevent="createAnalysis">
        <label class="start-label" for="document-id">已索引文档 ID</label>
        <div class="form-controls">
          <input id="document-id" v-model.number="documentId" type="number" min="1" required placeholder="例如 1" />
          <button class="generate-button" type="submit" :disabled="loading">
            {{ loading ? "分析中…" : "生成分析" }}
          </button>
        </div>
      </form>
      <p v-if="error" class="request-error" role="alert">{{ error }}</p>
    </section>

    <template v-else>
      <PaperAnalysisContextBar :analysis="analysis" :title="title" />
      <p v-if="error" class="request-error report-error" role="alert">{{ error }}</p>
      <div class="analysis-shell">
        <PaperOutline class="outline-panel" :available-sections="availableOutlineSections" @navigate="scrollToLabel" />
        <section class="report-panel" aria-label="分析报告">
          <PaperHeader :analysis="analysis" :busy="loading" @back="goBack" @regenerate="regenerate" />
          <ResearchBrief :title="title" :author="author" :analysis="analysis" :confidence="confidence" />
          <div v-if="blocks.length === 0" class="no-blocks">
            <p>结构化分析结果未提供。请查看当前分析状态，或在完成后重新生成分析。</p>
          </div>
          <div v-else class="block-list">
            <InsightBlock v-for="block in blocks" :key="block.field" :block="block" @jump="handleJump" />
          </div>
          <PaperMetadataBar :study-type="studyType" :sample-size="sampleSize" :evidence-count="analysis.sources.length" />
        </section>
        <EvidenceRail
          class="grid-rail"
          :class="{ 'rail-open': railOpen }"
          :cards="evidenceCards"
          :source-kinds="sourceKinds"
          @jump="handleJump"
        />
      </div>
      <button class="rail-toggle" type="button" :aria-expanded="railOpen" @click="toggleRail">
        {{ railOpen ? "收起原文证据" : "查看原文证据" }}
      </button>
    </template>
  </main>
</template>

<style scoped>
.analysis-page {
  width: min(100% - 3rem, 1440px);
  min-height: calc(100vh - 65px);
  margin: 0 auto;
  padding: 1.55rem 0 2.5rem;
}
.page-header {
  margin-bottom: 1rem;
}
.eyebrow {
  margin: 0 0 0.35rem;
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.12em;
}
.page-title {
  margin: 0;
  color: var(--text-primary);
  font-size: clamp(1.65rem, 2.4vw, 2.1rem);
  line-height: 1.2;
}
.page-description {
  max-width: 720px;
  margin: 0.45rem 0 0;
  color: var(--text-muted);
}
.analysis-tab {
  display: flex;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border-subtle);
}
.analysis-tab-current {
  padding: 0.55rem 0.85rem;
  border-bottom: 2px solid var(--color-primary);
  color: var(--color-primary);
  font-size: 0.88rem;
  font-weight: 800;
}
.empty-panel {
  display: grid;
  gap: 0.85rem;
  width: min(100%, 720px);
  padding: 1.4rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow);
}
.empty-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.15rem;
}
.empty-copy {
  max-width: 610px;
  margin: 0;
  color: var(--text-muted);
}
.start-form {
  display: grid;
  gap: 0.4rem;
}
.start-label {
  color: var(--text-primary);
  font-size: 0.84rem;
  font-weight: 750;
}
.form-controls {
  display: flex;
  gap: 0.65rem;
}
.form-controls input {
  flex: 1;
  min-width: 0;
  padding: 0.66rem 0.75rem;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  font: inherit;
}
.generate-button {
  padding: 0.66rem 1rem;
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
}
.generate-button:disabled {
  opacity: 0.6;
}
.request-error {
  margin: 0;
  padding: 0.75rem 0.85rem;
  border-radius: 8px;
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.report-error {
  margin-bottom: 0.85rem;
}
.analysis-shell {
  display: grid;
  grid-template-columns: minmax(165px, 18%) minmax(0, 1fr) minmax(225px, 24%);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.outline-panel {
  border-right: 1px solid var(--border-subtle);
  background: var(--surface);
}
.report-panel {
  display: grid;
  align-content: start;
  gap: 0.9rem;
  min-width: 0;
  padding: 1.1rem 1.35rem 1.5rem;
  background: var(--page-bg);
}
.grid-rail {
  border-left: 1px solid var(--border-subtle);
  background: var(--surface);
}
.no-blocks {
  padding: 1rem;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  color: var(--text-muted);
}
.no-blocks p {
  margin: 0;
}
.block-list {
  display: grid;
  gap: 0.75rem;
}
.rail-toggle {
  display: none;
}
@media (max-width: 1100px) {
  .analysis-shell {
    grid-template-columns: minmax(0, 1fr);
  }
  .grid-rail {
    display: none;
  }
  .grid-rail.rail-open {
    display: block;
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 40;
    max-height: 60vh;
    overflow-y: auto;
    border-top: 1px solid var(--border-strong);
    border-left: 0;
    box-shadow: 0 -12px 40px rgba(15, 23, 42, 0.18);
  }
  .rail-toggle {
    display: block;
    position: fixed;
    right: 1rem;
    bottom: 1rem;
    z-index: 41;
    padding: 0.6rem 1rem;
    border: 1px solid var(--border-strong);
    border-radius: 99px;
    background: var(--surface);
    box-shadow: var(--shadow);
    color: var(--text-primary);
    font-weight: 750;
  }
}
@media (max-width: 900px) {
  .analysis-page {
    width: min(100% - 2rem, 1440px);
  }
  .outline-panel {
    display: none;
  }
}
@media (max-width: 620px) {
  .form-controls {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
