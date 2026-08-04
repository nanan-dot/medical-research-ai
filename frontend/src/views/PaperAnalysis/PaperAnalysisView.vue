<script setup lang="ts">
import { computed, ref } from "vue";
import { paperAnalysisApi, type PaperAnalysis } from "../../api/paperAnalysis";
import EvidenceRail from "../../components/paper/EvidenceRail.vue";
import InsightBlock from "../../components/paper/InsightBlock.vue";
import PaperHeader from "../../components/paper/PaperHeader.vue";
import PaperMetadataBar from "../../components/paper/PaperMetadataBar.vue";
import PaperOutline from "../../components/paper/PaperOutline.vue";
import ResearchBrief from "../../components/paper/ResearchBrief.vue";
import {
  overallConfidence,
  toEvidenceCards,
  toInsightBlocks,
  type ConfidenceLevel,
  type InsightBlockModel,
} from "../../components/paper/paperModel";

const documentId = ref<number | null>(null);
const analysis = ref<PaperAnalysis | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const railOpen = ref(false);

const evidenceCards = computed(() => toEvidenceCards(analysis.value?.sources ?? []));
const blocks = computed<InsightBlockModel[]>(() =>
  analysis.value?.structured_result ? toInsightBlocks(analysis.value.structured_result, evidenceCards.value) : [],
);
const confidence = computed<ConfidenceLevel>(() =>
  analysis.value?.structured_result
    ? overallConfidence(Object.values(analysis.value.structured_result))
    : "needs-verification",
);

/** 元数据条缺少数值由组件渲染"未提供"，此处仅透传真实字段 */
const studyType = computed<string | null>(() => analysis.value?.structured_result?.study_type?.value ?? null);
const sampleSize = computed<string | null>(() => analysis.value?.structured_result?.sample_size?.value ?? null);

/** basic_information 文本同时承载标题与作者行，按行拆分后再拆分作者（；或,） */
const title = computed<string | null>(() => {
  const value = analysis.value?.structured_result?.basic_information?.value;
  const firstLine = value?.split("\n")[0]?.trim();
  return firstLine || null;
});
const author = computed<string | null>(() => {
  const value = analysis.value?.structured_result?.basic_information?.value;
  const lines = value?.split("\n") ?? [];
  if (lines.length <= 1) return null;
  const authorsLine = lines.slice(1).join("\n");
  const firstAuthor = authorsLine.split(/[；;]/)[0]?.trim();
  return firstAuthor || null;
});

async function createAnalysis() {
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

async function regenerate() {
  if (!analysis.value) return;
  loading.value = true;
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

function createMeetingDraft() {
  error.value = "前端原型将于 FE-06 开放；当前不会伪造组会汇报创建成功。";
}

function goBack() {
  // 返回上一页：后端未提供原文件打开，返回仅做浏览器级后退
  window.history.back();
}

function handleJump(localIndex: number) {
  // 来源定位：打开/保持证据栏并滚动到对应卡；原文件打开后端未提供，不做虚假跳转
  railOpen.value = true;
  const scroll = () => {
    const card = document.querySelector<HTMLElement>(`[aria-label="证据卡 ${localIndex + 1}"]`);
    card?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
    window.requestAnimationFrame(scroll);
  } else {
    scroll();
  }
}

/** 大纲章节 → 报告中实际存在的分析块标题（展示层映射，仅页内滚动） */
const SECTION_TO_BLOCK: Readonly<Record<string, readonly string[]>> = {
  abstract: ["一句话结论"],
  introduction: ["研究背景", "科学问题"],
  methods: ["研究设计", "对象和样本", "样本量", "干预或暴露", "对照", "统计方法"],
  results: ["主要结局", "主要结果"],
  discussion: ["创新", "局限", "下一步阅读"],
  references: ["原文证据"],
  figures: [],
};

function scrollToLabel(sectionKey: string) {
  // 大纲导航：仅滚动到真实存在的分析块；章节为展示层常量，不伪造章节真实分页
  const labels = SECTION_TO_BLOCK[sectionKey] ?? [];
  const heading = [...document.querySelectorAll<HTMLElement>("h3")].find((node) =>
    labels.includes(node.textContent?.trim() ?? ""),
  );
  if (heading) heading.scrollIntoView({ behavior: "smooth", block: "start" });
}

function toggleRail() {
  railOpen.value = !railOpen.value;
}
</script>

<template>
  <main class="workspace" aria-label="AI Research Workspace">
    <template v-if="!analysis?.structured_result">
      <PaperHeader
        :analysis="null"
        :busy="loading"
        @back="goBack"
        @regenerate="() => {}"
        @meeting="createMeetingDraft"
        @more="() => {}"
      />
      <section class="empty-state">
        <p class="eyebrow">AI RESEARCH WORKSPACE</p>
        <h1 class="empty-title">单篇论文阅读工作空间</h1>
        <p class="empty-copy">输入已建立索引的文档 ID 生成 AI 研究报告。每个结论都显示来源状态；模型推断不会冒充原文事实。</p>
        <form class="start-form" @submit.prevent="createAnalysis">
          <label class="start-label">
            文档 ID
            <input v-model.number="documentId" type="number" min="1" required placeholder="例如 1" />
          </label>
          <button class="start-button" type="submit" :disabled="loading">
            {{ loading ? "分析中…" : "生成报告" }}
          </button>
        </form>
        <p v-if="error" class="request-error" role="alert">{{ error }}</p>
      </section>
    </template>

    <template v-else>
      <div class="workspace-grid">
        <PaperOutline class="grid-outline" :sources="analysis.sources" @navigate="scrollToLabel" />
        <section class="grid-report">
          <PaperHeader
            :analysis="analysis"
            :busy="loading"
            @back="goBack"
            @regenerate="regenerate"
            @meeting="createMeetingDraft"
            @more="() => {}"
          />
          <ResearchBrief :title="title" :author="author" :analysis="analysis" :confidence="confidence" />
          <p v-if="error" class="request-error report-error" role="alert">{{ error }}</p>
          <div v-if="blocks.length === 0" class="no-blocks">
            <p>已生成分析但无结构化内容，可能处于生成中或失败状态。</p>
          </div>
          <div v-else class="block-list">
            <InsightBlock v-for="block in blocks" :key="block.field" :block="block" @jump="handleJump" />
          </div>
          <PaperMetadataBar :study-type="studyType" :sample-size="sampleSize" :evidence-count="analysis.sources.length" />
        </section>
        <EvidenceRail class="grid-rail" :class="{ 'rail-open': railOpen }" :cards="evidenceCards" @jump="handleJump" />
      </div>

      <button class="rail-toggle" type="button" :aria-expanded="railOpen" @click="toggleRail">
        {{ railOpen ? "收起证据栏" : "查看证据栏" }}
      </button>
    </template>
  </main>
</template>

<style scoped>
.workspace {
  min-height: calc(100vh - 65px);
  background: var(--page-bg);
}
.workspace-grid {
  display: grid;
  grid-template-columns: 18% minmax(0, 57%) minmax(0, 25%);
  min-height: calc(100vh - 65px);
}
.grid-outline {
  border-right: 1px solid var(--border-subtle);
  background: var(--surface-raised);
}
.grid-report {
  display: grid;
  gap: 1rem;
  align-content: start;
  padding: 1.15rem 1.5rem 2.5rem;
  min-width: 0;
  background: var(--page-bg);
}
.grid-rail {
  border-left: 1px solid var(--border-subtle);
  background: var(--surface-raised);
}

.empty-state {
  max-width: 720px;
  margin: auto;
  padding: 3rem 1.5rem 2rem;
  display: grid;
  gap: 0.9rem;
}
.eyebrow {
  margin: 0;
  color: var(--color-primary);
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.12em;
}
.empty-title {
  margin: 0;
  font-size: clamp(1.6rem, 3vw, 2.4rem);
  color: var(--text-primary);
  line-height: 1.2;
}
.empty-copy {
  margin: 0;
  color: var(--text-muted);
  max-width: 620px;
}
.start-form {
  display: flex;
  gap: 0.7rem;
  align-items: end;
  padding: 1rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow);
}
.start-label {
  display: grid;
  gap: 0.35rem;
  flex: 1;
  font-weight: 700;
  color: var(--text-primary);
}
.start-label input {
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  font: inherit;
}
.start-button {
  padding: 0.7rem 1.1rem;
  border: 0;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 750;
}
.start-button:disabled {
  opacity: 0.6;
}
.request-error {
  margin: 0;
  padding: 0.8rem;
  border-radius: 10px;
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.report-error {
  align-self: start;
}
.no-blocks {
  padding: 1.2rem;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  color: var(--text-muted);
}
.block-list {
  display: grid;
  gap: 0.85rem;
}
.rail-toggle {
  display: none;
}

/* <1100px：右侧证据栏折叠为底部抽屉 */
@media (max-width: 1100px) {
  .workspace-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .workspace-grid .grid-rail {
    display: none;
  }
  .workspace-grid .grid-rail.rail-open {
    display: block;
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 40;
    max-height: 60vh;
    overflow-y: auto;
    border-left: 0;
    border-top: 1px solid var(--border-strong);
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
    font-weight: 750;
    transition: background-color 0.15s, border-color 0.15s;
  }
  .rail-toggle:hover {
    border-color: var(--color-primary);
    background: var(--color-primary-soft);
  }
}

/* <900px：左侧导航隐藏 */
@media (max-width: 900px) {
  .grid-outline {
    display: none;
  }
}
</style>
