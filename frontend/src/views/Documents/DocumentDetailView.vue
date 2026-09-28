<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute } from "vue-router";

import DocumentDetailOverview from "../../components/document/DocumentDetailOverview.vue";
import DocumentDetailHeader from "../../components/document/DocumentDetailHeader.vue";
import DocumentAnnotationWorkspace from "../../components/document/DocumentAnnotationWorkspace.vue";
import DocumentOcrPanel from "../../components/document/DocumentOcrPanel.vue";
import DocumentPreviewPanel from "../../components/document/DocumentPreviewPanel.vue";
import StatePanel from "../../components/ui/StatePanel.vue";
import { useDocumentDetail } from "../../composables/useDocumentDetail";

const route = useRoute();
const documentId = Number(route.params.id);
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

</script>

<template>
  <main class="detail-page">
    <StatePanel
      v-if="loading"
      title="正在读取资料状态"
      description="正在加载真实的本地资料记录。"
    />
    <StatePanel v-else-if="error" title="资料不可用" :description="error">
      <button class="retry-button" @click="load">重试</button>
    </StatePanel>
    <div v-else-if="document" class="detail-layout">
      <DocumentDetailHeader :document="document" />
      <DocumentAnnotationWorkspace v-if="preview?.kind === 'pdf' && preview.content_url && document.parse_status === 'succeeded'" :document="document" :source-url="preview.content_url" :summary="summary" :action-loading="actionLoading" @retry-parse="retryParse" @retry-index="retryIndex" />
      <template v-else>
      <div class="primary-column">
        <DocumentPreviewPanel
          :preview="preview"
          :document="document"
          :loading="previewLoading"
          :error-message="previewError"
          @retry="loadPreview"
        />
      </div>
      <aside class="detail-sidebar">
        <DocumentDetailOverview
          :document="document"
          :summary="summary"
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
          v-if="document.error_message"
          title="处理错误"
          :description="document.error_message"
        />
      </aside>
      </template>
    </div>
  </main>
</template>

<style scoped>
.detail-page { width: min(100% - 2rem, 1440px); margin: 0 auto; padding: 1.25rem 0 2.8rem; }
.detail-layout { display: grid; gap: 1rem; align-items: start; }
.primary-column, .detail-sidebar { min-width: 0; }
.detail-sidebar { display: grid; gap: 1rem; }
.retry-button { border: 1px solid var(--border-strong); border-radius: 7px; padding: .45rem .7rem; background: var(--paper); color: var(--text-primary); font: inherit; }
@media (max-width: 1024px) { .detail-page { width: min(100% - 1.5rem, 900px); padding-top: 1rem; }.detail-layout { grid-template-columns: 1fr; } }
</style>
