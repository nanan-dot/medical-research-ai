<script setup lang="ts">
import { reactive } from "vue";

import type { CreateKnowledgeSource, KnowledgeSourceType } from "../../api/knowledgeSources";

defineProps<{ disabled: boolean }>();
const emit = defineEmits<{ submit: [payload: CreateKnowledgeSource] }>();

const form = reactive<CreateKnowledgeSource>({
  name: "",
  source_type: "local_folder",
  root_path: "",
});

const sourceTypes: Array<{ value: KnowledgeSourceType; label: string }> = [
  { value: "local_folder", label: "本地文件夹" },
  { value: "obsidian_vault", label: "Obsidian Vault" },
  { value: "temporary_import", label: "临时导入目录" },
];

function submit(): void {
  emit("submit", { ...form });
}
</script>

<template>
  <form class="source-form" @submit.prevent="submit">
    <label class="field">
      <span class="field-label">名称</span>
      <input v-model.trim="form.name" required maxlength="200" placeholder="例如：课题组论文" />
    </label>
    <label class="field">
      <span class="field-label">类型</span>
      <select v-model="form.source_type">
        <option v-for="type in sourceTypes" :key="type.value" :value="type.value">
          {{ type.label }}
        </option>
      </select>
    </label>
    <label class="field field-wide">
      <span class="field-label">授权目录</span>
      <input v-model.trim="form.root_path" required placeholder="H:\research\papers" />
    </label>
    <button class="primary-action" type="submit" :disabled="disabled">添加知识源</button>
  </form>
</template>

<style scoped>
.source-form { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.field { display: grid; gap: 0.45rem; }
.field-wide { grid-column: 1 / -1; }
.field-label { color: #52626b; font-size: 0.82rem; font-weight: 700; }
.field input, .field select { border: 1px solid #c8d4d8; border-radius: 10px; padding: 0.78rem; background: #fff; color: #17262d; }
.primary-action { justify-self: start; border: 0; border-radius: 10px; padding: 0.75rem 1rem; background: #0d6f66; color: #fff; font-weight: 700; cursor: pointer; }
.primary-action:disabled { cursor: wait; opacity: 0.55; }
@media (max-width: 680px) { .source-form { grid-template-columns: 1fr; } .field-wide { grid-column: auto; } }
</style>
