<script setup lang="ts">
import { shallowRef, watch } from "vue";
import { ApiError } from "../../api/client";
import { sourceAnchorsApi, type AnchoredReadingNote } from "../../api/sourceAnchors";
import type { PdfTextSelection } from "../../types/documentAnnotations";

const props = defineProps<{ documentId: number; selection: PdfTextSelection | null }>();
const emit = defineEmits<{ revisionConflict: [] }>();
const notes = shallowRef<AnchoredReadingNote[]>([]);
const content = shallowRef("");
const frozenSelection = shallowRef<PdfTextSelection | null>(null);
const saving = shallowRef(false);
const error = shallowRef("");
let generation = 0;
let requestBody = "", requestKey = "";

watch(() => props.documentId, async (id) => {
  const current = ++generation; notes.value = []; frozenSelection.value = null;
  try {
    const result = await sourceAnchorsApi.notes(id);
    // API 失败页或旧代理的非数组响应不应污染已挂载的笔记列表。
    if (current === generation) notes.value = Array.isArray(result) ? result : [];
  }
  catch (cause) { if (current === generation) error.value = cause instanceof Error ? cause.message : "笔记加载失败"; }
}, { immediate: true });
watch(() => props.selection, selection => { if (!selection) frozenSelection.value = null; });

async function save() {
  const descriptor = (frozenSelection.value ?? props.selection)?.anchorDescriptor;
  if (!descriptor || saving.value || !content.value.trim()) return;
  const current = generation, documentId = props.documentId;
  const body = JSON.stringify([documentId, descriptor, content.value]);
  if (body !== requestBody) { requestBody = body; requestKey = crypto.randomUUID(); }
  saving.value = true; error.value = "";
  try {
    const note = await sourceAnchorsApi.saveNote(documentId, descriptor, content.value, requestKey);
    if (current !== generation) return;
    notes.value = [...notes.value.filter(item => item.id !== note.id), note];
    content.value = ""; frozenSelection.value = null; requestBody = "";
  } catch (cause) {
    if (current !== generation) return;
    error.value = cause instanceof Error ? cause.message : "笔记保存失败";
    if (cause instanceof ApiError && cause.code?.includes("REVISION_CONFLICT")) {
      frozenSelection.value = null; emit("revisionConflict");
    }
  } finally { saving.value = false; }
}
</script>

<template>
  <section class="reading-notes" aria-label="原文笔记">
    <h3>原文笔记</h3>
    <label>笔记内容<textarea v-model="content" rows="3" maxlength="8000" :disabled="saving" @focus="frozenSelection = props.selection" /></label>
    <button :disabled="saving || !props.selection?.anchorDescriptor || !content.trim()" @click="save">{{ saving ? "正在保存笔记…" : "保存笔记" }}</button>
    <p v-if="error" role="alert">{{ error }}</p>
    <article v-for="note in notes" :key="note.id">
      <blockquote>{{ note.quote }}</blockquote><p>{{ note.content }}</p>
    </article>
  </section>
</template>

<style scoped>
.reading-notes { display: grid; gap: .6rem; border-top: 1px solid var(--border-subtle); padding-top: 1rem; }
h3, p { margin: 0; } h3 { font-size: 1rem; } label { display: grid; gap: .3rem; font-size: .8rem; }
textarea { width: 100%; box-sizing: border-box; border: 1px solid var(--border-strong); border-radius: 7px; padding: .5rem; background: var(--paper); color: var(--text-primary); font: inherit; }
button { justify-self: start; padding: .5rem .7rem; border: 1px solid var(--border-strong); border-radius: 7px; background: var(--paper); color: var(--text-primary); }
blockquote { margin: .5rem 0; padding-left: .6rem; border-left: 2px solid var(--border-strong); color: var(--text-muted); font-size: .8rem; }
</style>
