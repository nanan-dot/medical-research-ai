<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

import { resourceLibraryApi, type ResourceImportItem } from "../../api/resourceLibrary";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: []; imported: [items: ResourceImportItem[]] }>();

const files = ref<File[]>([]);
const results = ref<ResourceImportItem[]>([]);
const error = ref<string | null>(null);
const submitting = ref(false);
const dialog = ref<HTMLElement | null>(null);
let opener: HTMLElement | null = null;

const hasQueuedFiles = computed(() => files.value.length > 0);
const hasCompletedImport = computed(() => results.value.length > 0);

watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    opener = globalThis.document.activeElement instanceof HTMLElement ? globalThis.document.activeElement : null;
    await nextTick();
    dialog.value?.focus();
  } else {
    await nextTick();
    opener?.focus();
  }
});

function setFiles(nextFiles: FileList | File[]): void {
  files.value = Array.from(nextFiles);
  results.value = [];
  error.value = null;
}

function onFileChange(event: Event): void {
  const input = event.currentTarget as HTMLInputElement;
  setFiles(input.files ?? []);
  input.value = "";
}

function onDrop(event: DragEvent): void {
  event.preventDefault();
  if (event.dataTransfer?.files.length) setFiles(event.dataTransfer.files);
}

async function submit(): Promise<void> {
  if (!hasQueuedFiles.value || hasCompletedImport.value || submitting.value) return;
  submitting.value = true;
  error.value = null;
  try {
    const response = await resourceLibraryApi.imports(files.value);
    results.value = response.items;
    emit("imported", response.items);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "导入资料失败";
  } finally {
    submitting.value = false;
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && !submitting.value) emit("close");
}

function itemMessage(item: ResourceImportItem): string {
  if (item.status === "accepted" || item.status === "queued" || item.status === "created") return "上传完成，已进入后台处理任务";
  if (item.status === "duplicate") return "资料已存在，无需重复导入";
  if (item.message) return item.message;
  const messages: Readonly<Record<string, string>> = {
    invalid_signature: "PDF 文件内容无效或已损坏",
    invalid_pdf_signature: "PDF 文件内容无效或已损坏",
    unsupported_format: "暂不支持该文件格式",
    empty_file: "文件内容为空",
    upload_too_large: "文件超过允许的大小",
    too_many_files: "一次选择的文件过多",
  };
  return item.error_code ? messages[item.error_code] ?? "资料未能导入，请检查文件后重试" : "资料未能导入，请检查文件后重试";
}

function resultClass(item: ResourceImportItem): Record<string, boolean> {
  return {
    duplicate: item.status === "duplicate",
    failed: item.status === "failed" || item.status === "rejected",
    accepted: item.status === "accepted" || item.status === "queued" || item.status === "created",
  };
}
</script>

<template>
  <Teleport to="body">
    <div v-if="props.open" class="import-layer" @click.self="emit('close')">
      <section ref="dialog" class="import-dialog" role="dialog" aria-modal="true" aria-labelledby="import-title" tabindex="-1" @keydown="onKeydown">
        <header><div><h2 id="import-title">导入资料</h2><p>资料会进入处理任务，完成前不会显示为 AI 可使用。</p></div><button type="button" aria-label="关闭导入资料" :disabled="submitting" @click="emit('close')">×</button></header>
        <form @submit.prevent="submit">
          <label class="drop-zone" for="resource-import-files" @dragover.prevent @drop="onDrop">
            <input id="resource-import-files" type="file" multiple accept=".pdf,.doc,.docx,.pptx,.md,.markdown,.txt,application/pdf" @change="onFileChange">
            <strong>选择资料文件</strong><span>也可以将文件拖放到这里。支持的格式和大小限制由资料库服务决定。</span>
          </label>
          <ul v-if="files.length" class="file-list" aria-label="待导入资料"><li v-for="file in files" :key="`${file.name}-${file.size}`">{{ file.name }}</li></ul>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <ul v-if="results.length" class="result-list" aria-label="导入结果"><li v-for="result in results" :key="`${result.original_filename}-${result.document_id ?? result.error_code}`" :class="resultClass(result)"><strong>{{ result.original_filename }}</strong><span>{{ itemMessage(result) }}</span></li></ul>
          <footer><button type="button" :disabled="submitting" @click="emit('close')">取消</button><button class="submit" type="submit" :disabled="!hasQueuedFiles || hasCompletedImport || submitting">{{ submitting ? "正在导入…" : "导入资料" }}</button></footer>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.import-layer { position:fixed; z-index:50; inset:0; display:grid; place-items:center; padding:20px; background:rgb(15 23 42 / 32%); }.import-dialog { width:min(560px, 100%); max-height:min(720px, 100%); overflow:auto; padding:20px; border-radius:8px; background:var(--surface); box-shadow:var(--shadow-md, 0 8px 24px rgb(15 23 42 / 8%)); outline:0; }.import-dialog header { display:flex; justify-content:space-between; gap:16px; }.import-dialog h2 { margin:0; font-size:20px; }.import-dialog header p { margin:4px 0 0; color:var(--text-muted); font-size:13px; line-height:1.5; }.import-dialog header button { width:32px; height:32px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--surface); font:inherit; cursor:pointer; }.drop-zone { display:grid; gap:7px; margin-top:20px; padding:24px; border:1px dashed var(--color-primary); border-radius:8px; background:var(--color-primary-soft); color:var(--text-primary); cursor:pointer; text-align:center; }.drop-zone input { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0); }.drop-zone span { color:var(--text-muted); font-size:12px; line-height:1.5; }.file-list,.result-list { display:grid; gap:5px; margin:14px 0 0; padding:0; list-style:none; }.file-list li,.result-list li { display:flex; justify-content:space-between; gap:12px; padding:8px 10px; border:1px solid var(--border-subtle); border-radius:4px; color:var(--text-muted); font-size:12px; }.result-list strong { color:var(--text-primary); }.result-list .failed { border-color:var(--color-warning); color:var(--color-warning); }.error { color:var(--color-danger); font-size:13px; }.import-dialog footer { display:flex; justify-content:flex-end; gap:8px; margin-top:20px; }.import-dialog footer button { min-height:36px; border:1px solid var(--border-subtle); border-radius:4px; padding:0 12px; background:var(--surface); color:var(--text-primary); font:inherit; font-size:13px; font-weight:700; cursor:pointer; }.import-dialog footer .submit { border-color:var(--color-primary); background:var(--color-primary); color:#fff; }.import-dialog button:focus-visible,.drop-zone:focus-within { outline:2px solid var(--color-primary); outline-offset:2px; }.import-dialog button:disabled { cursor:not-allowed; opacity:.55; }@media(max-width:767px){.import-layer{place-items:end center;padding:0}.import-dialog{width:100%;max-height:85vh;border-radius:8px 8px 0 0;padding:18px;}} 
</style>
