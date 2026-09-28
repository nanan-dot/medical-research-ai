<script setup lang="ts">
import { computed, nextTick, shallowRef, watch } from "vue";

import { resourceLibraryApi, type ResourceImportItem } from "../../api/resourceLibrary";
import BaseIcon from "../ui/BaseIcon.vue";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: []; imported: [items: ResourceImportItem[]] }>();
const files = shallowRef<File[]>([]);
const results = shallowRef<ResourceImportItem[]>([]);
const error = shallowRef<string | null>(null);
const pending = shallowRef(false);
const dropZone = shallowRef<HTMLElement | null>(null);
const canSubmit = computed(() => files.value.length > 0 && !results.value.length && !pending.value);

function chooseFiles(source: FileList | readonly File[]): void {
  const selected = Array.from(source);
  const invalid = selected.find((file) => file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf"));
  if (invalid) { files.value = []; error.value = `“${invalid.name}”不是 PDF 文件`; return; }
  files.value = selected; results.value = []; error.value = null;
}
function fileChange(event: Event): void { const input = event.currentTarget as HTMLInputElement; chooseFiles(input.files ?? []); input.value = ""; }
function fileDrop(event: DragEvent): void { event.preventDefault(); if (event.dataTransfer?.files.length) chooseFiles(event.dataTransfer.files); }
async function submit(): Promise<void> {
  if (!canSubmit.value) return;
  pending.value = true; error.value = null;
  try { const response = await resourceLibraryApi.imports(files.value); results.value = response.items; emit("imported", response.items); }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "PDF 上传失败"; }
  finally { pending.value = false; }
}
function resultText(item: ResourceImportItem): string {
  if (["accepted", "queued", "created"].includes(item.status)) return "已上传并进入资料处理流程";
  if (item.status === "duplicate") return "资料已存在，将复用现有资料";
  return item.message ?? "未能导入";
}
function close(): void { if (!pending.value) emit("close"); }
watch(() => props.open, async (open) => { if (open) { files.value = []; results.value = []; error.value = null; await nextTick(); dropZone.value?.focus(); } });
</script>

<template>
  <Teleport to="body"><div v-if="open" class="upload-layer" @click.self="close"><section class="upload-dialog" role="dialog" aria-modal="true" aria-labelledby="upload-title" @keydown.esc.prevent="close"><header><div><h2 id="upload-title">上传论文 PDF</h2><p>文件先进入资料库处理；上传成功后会使用真实文档 ID 加入论文库。</p></div><button type="button" aria-label="关闭论文上传" :disabled="pending" @click="close"><BaseIcon name="close" /></button></header><form @submit.prevent="submit"><label ref="dropZone" class="drop-zone" for="paper-pdf-files" tabindex="0" @dragover.prevent @drop="fileDrop" @keydown.enter.prevent="($el as HTMLLabelElement).click()"><input id="paper-pdf-files" type="file" multiple accept=".pdf,application/pdf" @change="fileChange" /><BaseIcon name="document" /><b>选择论文 PDF</b><span>也可以拖放到这里。大小和数量限制由资料库服务统一校验。</span></label><ul v-if="files.length && !results.length" class="file-list"><li v-for="file in files" :key="`${file.name}-${file.size}`"><b>{{ file.name }}</b><span>{{ (file.size / 1024 / 1024).toFixed(1) }} MB</span></li></ul><ul v-if="results.length" class="result-list" aria-label="上传结果"><li v-for="result in results" :key="`${result.original_filename}-${result.document_id ?? result.error_code}`" :class="{ failed: ['failed', 'rejected'].includes(result.status) }"><b>{{ result.original_filename }}</b><span>{{ resultText(result) }}</span></li></ul><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" :disabled="pending" @click="close">{{ results.length ? "完成" : "取消" }}</button><button class="submit" type="submit" :disabled="!canSubmit">{{ pending ? "正在上传…" : "上传并加入论文库" }}</button></footer></form></section></div></Teleport>
</template>

<style scoped>
.upload-layer{position:fixed;z-index:61;inset:0;display:grid;place-items:center;padding:16px;background:rgb(15 23 42 / 30%)}.upload-dialog{width:min(560px,100%);max-height:90vh;overflow:auto;padding:20px;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 14px 42px rgb(15 23 42 / 16%)}header{display:flex;justify-content:space-between;gap:16px}h2{margin:0;font-size:18px}header p{margin:5px 0 0;color:#64748b;font-size:12px;line-height:1.5}header button{display:grid;width:32px;height:32px;place-items:center;border:0;background:transparent;color:#475569}header :deep(.icon){width:18px}.drop-zone{display:grid;place-items:center;margin-top:18px;border:1px dashed #78a9e8;border-radius:7px;padding:25px;background:#f7faff;color:#0b5fcc;text-align:center;cursor:pointer}.drop-zone input{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}.drop-zone :deep(.icon){width:28px;height:28px;margin-bottom:7px}.drop-zone b{color:#0f172a;font-size:13px}.drop-zone span{margin-top:4px;color:#64748b;font-size:11px}.file-list,.result-list{display:grid;gap:6px;margin:13px 0 0;padding:0;list-style:none}.file-list li,.result-list li{display:flex;justify-content:space-between;gap:12px;border:1px solid var(--line);border-radius:4px;padding:8px 10px;color:#64748b;font-size:11px}.file-list b,.result-list b{overflow:hidden;color:#334155;text-overflow:ellipsis;white-space:nowrap}.result-list .failed{border-color:#fecaca;color:#c52b2f}.error{color:#c52b2f;font-size:12px}footer{display:flex;justify-content:flex-end;gap:8px;margin-top:17px}footer button{height:36px;border:1px solid var(--line);border-radius:4px;padding:0 13px;background:#fff;color:#334155;font:inherit;font-size:12px;font-weight:700}.submit{border-color:#0b5fcc;background:#0b5fcc;color:#fff}button:disabled{cursor:not-allowed;opacity:.5}@media(max-width:540px){.upload-layer{align-items:end;padding:0}.upload-dialog{border-radius:10px 10px 0 0}}
</style>
