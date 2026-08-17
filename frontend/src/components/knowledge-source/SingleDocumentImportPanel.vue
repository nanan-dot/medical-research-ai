<script setup lang="ts">
import { computed, ref } from "vue";

import type { KnowledgeSource } from "../../api/knowledgeSources";

const props = defineProps<{ sources: readonly KnowledgeSource[]; submitting: boolean; error: string | null }>();
const emit = defineEmits<{ close: []; submit: [payload: { file: File; knowledgeSourceId?: number; newSourceName?: string; relativeDirectory?: string }] }>();

const file = ref<File | null>(null);
const assignment = ref<"existing" | "new">("existing");
const knowledgeSourceId = ref<number | null>(null);
const newSourceName = ref("");
const relativeDirectory = ref("");
const selectableSources = computed(() => props.sources.filter((source) => source.enabled));
const canSubmit = computed(() => file.value !== null && (assignment.value === "existing" ? knowledgeSourceId.value !== null : newSourceName.value.trim() !== ""));

function selectFile(event: Event): void {
  const input = event.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
}

function submit(): void {
  if (!file.value || !canSubmit.value) return;
  emit("submit", {
    file: file.value,
    knowledgeSourceId: assignment.value === "existing" ? knowledgeSourceId.value ?? undefined : undefined,
    newSourceName: assignment.value === "new" ? newSourceName.value.trim() : undefined,
    relativeDirectory: relativeDirectory.value.trim() || undefined,
  });
}
</script>

<template>
  <form class="import-form" @submit.prevent="submit">
    <label>选择 PDF 文件<input type="file" accept="application/pdf,.pdf" :disabled="submitting" @change="selectFile" /></label>
    <p v-if="file" class="file-summary">{{ file.name }} · {{ Math.ceil(file.size / 1024) }} KB · PDF</p>
    <fieldset :disabled="submitting">
      <legend>归属知识库</legend>
      <label><input v-model="assignment" type="radio" value="existing" /> 选择已有知识库</label>
      <label><input v-model="assignment" type="radio" value="new" /> 新建知识库</label>
    </fieldset>
    <label v-if="assignment === 'existing'">知识库
      <select v-model="knowledgeSourceId"><option :value="null">请选择知识库</option><option v-for="source in selectableSources" :key="source.id" :value="source.id">{{ source.name }} · {{ source.root_path }} · {{ source.stats.total_files }} 个文件</option></select>
    </label>
    <label v-else>新知识库名称<input v-model.trim="newSourceName" maxlength="200" required /></label>
    <label>逻辑子目录（可选）<input v-model.trim="relativeDirectory" placeholder="例如：2026/临床研究" /></label>
    <p v-if="error" class="request-error" role="alert">{{ error }}</p>
    <footer><button type="button" :disabled="submitting" @click="emit('close')">取消</button><button type="submit" :disabled="!canSubmit || submitting">{{ submitting ? "正在导入…" : "确认导入" }}</button></footer>
  </form>
</template>

<style scoped>
.import-form { display: grid; gap: 14px; }
label, fieldset { display: grid; gap: 6px; color: var(--ink-900); font-size: .9rem; }
fieldset { border: 0; margin: 0; padding: 0; }
fieldset label { display: flex; align-items: center; }
input, select { min-height: 36px; border: 1px solid var(--border-subtle); border-radius: 6px; padding: 6px 8px; font: inherit; }
.file-summary { margin: -6px 0 0; color: var(--text-muted); font-size: .8rem; }
footer { display: flex; justify-content: end; gap: 8px; }
button { border: 0; border-radius: 7px; padding: 8px 12px; font: inherit; font-weight: 700; }
button[type="submit"] { background: var(--color-primary); color: var(--surface); }
.request-error { color: var(--color-danger); }
</style>
