<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";

import DocumentDetailOverview from "../../components/document/DocumentDetailOverview.vue";
import DocumentOcrPanel from "../../components/document/DocumentOcrPanel.vue";
import DocumentPreviewPanel from "../../components/document/DocumentPreviewPanel.vue";
import StatePanel from "../../components/ui/StatePanel.vue";
import { useDocumentDetail } from "../../composables/useDocumentDetail";

const route = useRoute();
const router = useRouter();
const documentId = Number(route.params.id);
const shouldReturnToPaperResearch = computed(() => route.query.from === "analysis");
const {
  document,
  summary,
  preview,
  loading,
  previewLoading,
  actionLoading,
  error,
  previewError,
  load,
  loadPreview,
  retryParse,
  retryIndex,
} = useDocumentDetail(documentId);

onMounted(load);

function returnToPaperResearch(): void {
  void router.push({ path: "/analysis", query: { documentId: String(documentId) } });
}
</script>

<template>
  <main class="detail-page">
    <StatePanel
      v-if="loading"
      title="正在读取文档状态"
      description="正在加载真实的本地文档记录。"
    />
    <StatePanel v-else-if="error" title="文档不可用" :description="error">
      <button class="retry-button" @click="load">重试</button>
    </StatePanel>
    <div v-else-if="document" class="detail-layout">
      <div v-if="shouldReturnToPaperResearch" class="workflow-return">
        <button type="button" @click="returnToPaperResearch">← 返回论文研究</button>
        <span>将保留当前文档作为论文研究上下文。</span>
      </div>
      <div class="primary-column">
        <DocumentPreviewPanel
          :preview="preview"
          :document="document"
          :loading="previewLoading"
          :error-message="previewError"
          @retry="loadPreview"
        />
      </div>
      <aside class="sidebar">
        <DocumentDetailOverview
          :document="document"
          :action-loading="actionLoading"
          @retry-parse="retryParse"
          @retry-index="retryIndex"
        />
        <DocumentOcrPanel
          :document-id="document.id"
          :is-scanned="document.parsed_is_scanned === true"
          @completed="load"
        />
        <StatePanel
          v-if="summary"
          title="真实内容摘要"
          :description="`共 ${summary.page_count} 页，${summary.character_count} 个字符。`"
        >
          <p v-if="summary.is_scanned">扫描件 PDF：可在支持时发起 OCR。</p>
          <p v-else>章节：{{ summary.section_headings.join(' · ') || '未解析到章节' }}</p>
        </StatePanel>
        <StatePanel
          v-if="document.error_message"
          title="处理错误"
          :description="document.error_message"
        />
      </aside>
    </div>
  </main>
</template>

<style scoped>
.detail-page { width: min(100% - 2rem, 1280px); margin: 0 auto; padding: 2rem 0 2.8rem; }
.detail-layout { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, .85fr); gap: 1.25rem; align-items: start; }
.workflow-return { grid-column: 1 / -1; display: flex; align-items: center; gap: .65rem; padding: .65rem .75rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface); color: var(--text-muted); font-size: .84rem; }
.workflow-return button { border: 0; background: transparent; color: var(--color-primary); font: inherit; font-weight: 800; cursor: pointer; }
.primary-column, .sidebar { min-width: 0; }
.sidebar { display: grid; gap: 1rem; }
.retry-button { border: 1px solid var(--border-strong); border-radius: 7px; padding: .45rem .7rem; background: var(--paper); color: var(--text-primary); font: inherit; }
@media (max-width: 860px) { .detail-page { width: min(100% - 1.5rem, 760px); padding-top: 1rem; }.detail-layout { grid-template-columns: 1fr; }.sidebar { order: -1; } }
</style>
