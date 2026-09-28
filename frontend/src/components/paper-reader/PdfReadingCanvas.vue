<script setup lang="ts">
import { shallowRef, useTemplateRef } from "vue";
import type { ReaderBootstrap } from "../../api/paperReader";
import type { AnnotationColor } from "../../api/documentAnnotations";
import { useDocumentAnnotations } from "../../composables/useDocumentAnnotations";
import type { PdfTextSelection } from "../../types/documentAnnotations";
import PdfAnnotationReader from "../document/PdfAnnotationReader.vue";

const props = defineProps<{ bootstrap: ReaderBootstrap }>();
const emit = defineEmits<{
  recordsChanged: [];
  selectionChanged: [selection: PdfTextSelection | null];
  translateSelection: [];
}>();
const selection = shallowRef<PdfTextSelection | null>(null);
const noteOpen = shallowRef(false);
const noteText = shallowRef("");
const reader =
  useTemplateRef<InstanceType<typeof PdfAnnotationReader>>("reader");
const { annotations, saving, error, create } = useDocumentAnnotations(
  () => props.bootstrap.paper.document_id,
  () => props.bootstrap.document.file_hash,
);
async function saveHighlight(color: AnnotationColor): Promise<void> {
  if (!selection.value) return;
  const saved = await create({
    page_number: selection.value.pageNumber,
    rectangles: selection.value.rectangles,
    selected_text: selection.value.selectedText,
    anchor_descriptor: selection.value.anchorDescriptor,
    color,
    note: null,
  });
  if (saved) selection.value = null;
}
async function saveNote(): Promise<void> {
  if (!selection.value || !noteText.value.trim()) return;
  const saved = await create({
    page_number: selection.value.pageNumber,
    rectangles: selection.value.rectangles,
    selected_text: selection.value.selectedText,
    anchor_descriptor: selection.value.anchorDescriptor,
    color: "yellow",
    note: noteText.value.trim(),
  });
  if (saved) {
    selection.value = null;
    noteText.value = "";
    noteOpen.value = false;
    emit("recordsChanged");
  }
}
function updateSelection(value: PdfTextSelection | null): void {
  selection.value = value;
  emit("selectionChanged", value);
  if (!value) noteOpen.value = false;
}
async function goToPage(page: number): Promise<void> {
  await reader.value?.goToPage(page);
}
async function zoomBy(delta: number): Promise<void> {
  await reader.value?.zoomBy(delta);
}
defineExpose({
  locateSourceAnchor: (anchorId: number) =>
    reader.value?.locateSourceAnchor(anchorId),
  goToPage,
  zoomBy,
});
</script>
<template>
  <section class="canvas" :class="{ 'canvas--selection': selection }">
    <PdfAnnotationReader
      ref="reader"
      :source-url="bootstrap.document.content_url"
      :document-id="bootstrap.paper.document_id"
      :file-hash="bootstrap.document.file_hash"
      :annotations="annotations"
      :selected-annotation-id="null"
      :frozen="saving"
      @selection-change="updateSelection"
    />
    <div
      v-if="selection"
      class="selection-actions"
      role="toolbar"
      aria-label="选中文本操作"
    >
      <button type="button" @click="emit('translateSelection')">翻译</button
      ><button type="button" disabled title="术语服务尚未接入">术语</button
      ><button
        type="button"
        :aria-expanded="noteOpen"
        @click="noteOpen = !noteOpen"
      >
        笔记</button
      ><button
        type="button"
        :disabled="saving"
        @click="saveHighlight('yellow')"
      >
        {{ saving ? "保存中" : "高亮" }}</button
      ><button type="button" disabled title="请在论文库关联研究后加入研读">
        加入研读
      </button>
    </div>
    <form
      v-if="selection && noteOpen"
      class="note-editor"
      @submit.prevent="saveNote"
    >
      <label for="selection-note">为选中的原文添加笔记</label>
      <textarea
        id="selection-note"
        v-model="noteText"
        rows="3"
        maxlength="2000"
        placeholder="记录你的理解、疑问或结论…"
        autofocus
      ></textarea>
      <div>
        <button type="button" @click="noteOpen = false">取消</button
        ><button type="submit" :disabled="saving || !noteText.trim()">
          {{ saving ? "保存中…" : "保存笔记" }}
        </button>
      </div>
    </form>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </section>
</template>
<style scoped>
.canvas {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: calc(100vh - 150px);
  padding: 0 18px 18px;
  background: #f7f9fc;
}
.canvas :deep(.pdf-reader) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
}
.canvas :deep(.pdf-pages) {
  flex: 1;
  min-height: 0;
  max-height: none;
  border-color: #e5eaf2;
  background: #e8eef6;
  padding: 10px 0 16px;
  gap: 12px;
}
.canvas :deep(.reader-toolbar) {
  display: none;
}
.selection-actions {
  position: sticky;
  z-index: 3;
  bottom: 10px;
  display: flex;
  width: max-content;
  max-width: calc(100% - 24px);
  margin: 0 auto;
  padding: 5px;
  border-radius: 8px;
  background: #172033;
  box-shadow: 0 6px 18px rgb(17 24 39 / 20%);
}
.canvas--selection :deep(.thumbnail-strip) { margin-bottom: 4px; }
.selection-actions button {
  min-height: 32px;
  border: 0;
  border-right: 1px solid rgb(255 255 255 / 18%);
  padding: 0 10px;
  background: transparent;
  color: #fff;
  font: inherit;
  font-size: 12px;
}
.selection-actions button:disabled {
  opacity: 0.48;
}
.selection-actions button:last-child {
  border-right: 0;
}
.note-editor {
  position: sticky;
  z-index: 3;
  align-self: flex-end;
  margin: 8px 10px 0 0;
  display: grid;
  width: min(360px, calc(100% - 40px));
  gap: 8px;
  padding: 14px;
  border: 1px solid #dce4f0;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 12px 30px rgb(17 24 39 / 18%);
}
.note-editor label {
  color: #182235;
  font-size: 13px;
  font-weight: 750;
}
.note-editor textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid #cbd7e8;
  border-radius: 7px;
  padding: 9px;
  font: inherit;
  resize: vertical;
}
.note-editor div {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.note-editor button {
  min-height: 34px;
  border: 1px solid #dce4f0;
  border-radius: 6px;
  padding: 0 12px;
  background: #fff;
  color: #344054;
  font: inherit;
}
.note-editor button[type="submit"] {
  border-color: #0868f7;
  background: #0868f7;
  color: #fff;
  font-weight: 700;
}
.note-editor button:disabled {
  opacity: 0.5;
}
.error {
  color: #b42318;
}
@media (max-width: 1023px) {
  .canvas {
    height: calc(100vh - 190px);
    padding-inline: 8px;
  }
}
</style>
