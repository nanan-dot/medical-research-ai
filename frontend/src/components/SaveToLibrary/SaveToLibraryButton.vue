<script setup lang="ts">
import { shallowRef } from "vue";
import { literatureSearchApi, type LibraryItem } from "../../api/literatureSearch";

const props = defineProps<{ resultId: number; pmid: string; disabled: boolean }>();
const emit = defineEmits<{ saved: [item: LibraryItem] }>();
const saving = shallowRef(false);
const error = shallowRef("");

async function save(): Promise<void> {
  saving.value = true; error.value = "";
  try { emit("saved", await literatureSearchApi.saveToLibrary(props.resultId, props.pmid)); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "保存到本地知识库失败"; }
  finally { saving.value = false; }
}
</script>

<template>
  <span class="save-library">
    <button class="button" :disabled="disabled || saving" @click="save">{{ saving ? "保存中…" : "加入知识库" }}</button>
    <small v-if="error" class="error" role="alert">{{ error }}</small>
  </span>
</template>

<style scoped>
.save-library { display: grid; gap: .25rem; }
.button { border: 1px solid var(--border-strong); border-radius: 99px; padding: .3rem .6rem; background: var(--paper); color: var(--color-primary); font-size: .76rem; font-weight: 750; white-space: nowrap; }
.button:disabled { opacity: .55; }
.error { color: var(--color-danger); max-width: 14rem; }
</style>
