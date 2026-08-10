<script setup lang="ts">
import type { DocumentPreview } from "../../api/documentPreviews";
import type { DocumentRecord } from "../../api/documents";
import StatePanel from "../ui/StatePanel.vue";
import DocumentAnnotationWorkspace from "./DocumentAnnotationWorkspace.vue";

const props = defineProps<{
  preview: Readonly<DocumentPreview> | null;
  document: DocumentRecord | null;
  loading: boolean;
  errorMessage: string | null;
}>();

const emit = defineEmits<{
  retry: [];
}>();

function blockClass(kind: DocumentPreview["blocks"][number]["kind"]): string {
  return `preview-block-${kind}`;
}
</script>

<template>
  <section class="preview-panel" aria-labelledby="preview-title">
    <header class="preview-header">
      <div>
        <p class="eyebrow">READ-ONLY ORIGINAL</p>
        <h2 id="preview-title" class="preview-title">在线预览</h2>
      </div>
    </header>

    <StatePanel
      v-if="props.loading"
      title="正在加载原文预览"
      description="正在通过受控文档接口读取预览信息。"
    />
    <StatePanel v-else-if="props.errorMessage" title="预览不可用" :description="props.errorMessage">
      <button class="retry-button" @click="emit('retry')">重试</button>
    </StatePanel>
    <StatePanel
      v-else-if="props.preview?.kind === 'unavailable'"
      title="暂不支持预览"
      :description="props.preview.message ?? '该文件暂不支持在线预览。'"
    />
    <DocumentAnnotationWorkspace
      v-else-if="props.preview?.kind === 'pdf' && props.preview.content_url && props.document?.parse_status === 'succeeded'"
      :document="props.document"
      :source-url="props.preview.content_url"
    />
    <iframe
      v-else-if="props.preview?.kind === 'pdf' && props.preview.content_url"
      class="pdf-frame"
      :src="props.preview.content_url"
      title="PDF 原文只读预览"
      sandbox=""
      referrerpolicy="no-referrer"
    />
    <div v-else-if="props.preview?.kind === 'docx'" class="docx-preview">
      <template v-for="(block, index) in props.preview.blocks" :key="`${block.kind}-${index}`">
        <h3 v-if="block.kind === 'heading'" :class="blockClass(block.kind)">{{ block.text }}</h3>
        <li v-else-if="block.kind === 'list_item'" :class="blockClass(block.kind)">{{ block.text }}</li>
        <p v-else :class="blockClass(block.kind)">{{ block.text }}</p>
      </template>
      <div v-for="(table, tableIndex) in props.preview.tables" :key="tableIndex" class="table-wrap">
        <table class="docx-table">
          <tbody>
            <tr v-for="(row, rowIndex) in table.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.preview-panel { display: grid; gap: .85rem; }
.preview-header { display: flex; justify-content: space-between; }
.eyebrow { margin: 0; color: var(--color-primary); font-weight: 900; font-size: .72rem; letter-spacing: .12em; }
.preview-title { margin: .2rem 0 0; font-size: 1.2rem; }
.pdf-frame { width: 100%; min-height: 680px; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface-muted); }
.docx-preview { display: grid; gap: .8rem; padding: 1.15rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--paper); line-height: 1.65; }
.preview-block-heading { margin: .4rem 0 0; color: var(--text-primary); font-size: 1.12rem; }
.preview-block-paragraph, .preview-block-list_item { margin: 0; color: var(--text-primary); white-space: pre-wrap; }
.preview-block-list_item { margin-left: 1.2rem; }
.table-wrap { overflow-x: auto; }
.docx-table { width: 100%; border-collapse: collapse; }
.docx-table td { min-width: 100px; padding: .55rem; border: 1px solid var(--border-subtle); vertical-align: top; }
.retry-button { border: 1px solid var(--border-strong); border-radius: 7px; padding: .45rem .7rem; background: var(--paper); color: var(--text-primary); font: inherit; }
@media (max-width: 700px) { .pdf-frame { min-height: 460px; } }
</style>
