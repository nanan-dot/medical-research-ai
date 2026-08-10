<script setup lang="ts">
import { shallowRef } from "vue";

const props = defineProps<{
  uploading: boolean;
  errorMessage: string | null;
  uploadedFilename: string | null;
}>();

const emit = defineEmits<{
  upload: [file: File];
}>();

const isDragActive = shallowRef(false);
const validationMessage = shallowRef<string | null>(null);

function selectFile(file: File | undefined): void {
  validationMessage.value = null;
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf") || !isPdfMimeType(file.type)) {
    validationMessage.value = "请选择 MIME 类型为 application/pdf 的 PDF 文件。";
    return;
  }
  emit("upload", file);
}

function handleInputChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  selectFile(input.files?.[0]);
  input.value = "";
}

function handleDrop(event: DragEvent): void {
  isDragActive.value = false;
  selectFile(event.dataTransfer?.files[0]);
}

function isPdfMimeType(mediaType: string): boolean {
  return mediaType === "application/pdf" || mediaType === "application/x-pdf";
}
</script>

<template>
  <section class="upload-panel" aria-labelledby="upload-title">
    <div>
      <p class="eyebrow">SINGLE PDF UPLOAD</p>
      <h3 id="upload-title" class="upload-title">上传一份 PDF</h3>
      <p class="upload-description">文件将在受控存储中校验并建立文档记录；单文件上限 50 MiB。</p>
    </div>

    <label
      class="drop-zone"
      :class="{ 'drop-zone-active': isDragActive, 'drop-zone-disabled': props.uploading }"
      @dragenter.prevent="isDragActive = true"
      @dragover.prevent="isDragActive = true"
      @dragleave.prevent="isDragActive = false"
      @drop.prevent="handleDrop"
    >
      <input
        class="file-input"
        type="file"
        accept="application/pdf,.pdf"
        :disabled="props.uploading"
        @change="handleInputChange"
      />
      <span class="drop-zone-title">{{ props.uploading ? "正在上传并校验…" : "拖入 PDF，或点击选择文件" }}</span>
      <span class="drop-zone-note">仅支持单个、未加密的 PDF</span>
    </label>

    <p v-if="props.uploadedFilename" class="upload-success" role="status">
      已上传 {{ props.uploadedFilename }}，文档列表已刷新，等待解析。
    </p>
    <p v-if="validationMessage || props.errorMessage" class="upload-error" role="alert">
      {{ validationMessage ?? props.errorMessage }}
    </p>
  </section>
</template>

<style scoped>
.upload-panel { display: grid; gap: .8rem; padding: 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface-muted); }
.eyebrow { margin: 0; color: var(--color-primary); font-size: .72rem; font-weight: 900; letter-spacing: .14em; }
.upload-title { margin: .18rem 0 0; font-size: 1.08rem; }
.upload-description { margin: .35rem 0 0; color: var(--text-muted); font-size: .85rem; line-height: 1.5; }
.drop-zone { display: grid; gap: .35rem; padding: .9rem; border: 1px dashed var(--border-strong); border-radius: 9px; background: var(--paper); cursor: pointer; transition: border-color .15s ease, background-color .15s ease; }
.drop-zone-active { border-color: var(--color-primary); background: var(--color-primary-soft); }
.drop-zone-disabled { cursor: wait; opacity: .72; }
.file-input { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap; }
.drop-zone-title { color: var(--text-primary); font-weight: 800; }
.drop-zone-note { color: var(--text-muted); font-size: .78rem; }
.upload-success, .upload-error { margin: 0; padding: .7rem .8rem; border-radius: 8px; font-size: .85rem; }
.upload-success { background: var(--color-success-soft); color: var(--color-success); }
.upload-error { background: var(--color-danger-soft); color: var(--color-danger); }
</style>
