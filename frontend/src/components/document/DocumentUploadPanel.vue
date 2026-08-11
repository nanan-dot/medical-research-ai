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
  <section class="upload-panel" aria-label="上传 PDF">
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
      <span class="drop-zone-title">{{ props.uploading ? "正在上传并校验…" : "上传 PDF" }}</span>
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
.upload-panel{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap}.drop-zone{display:inline-flex;padding:.62rem 1rem;border:0;border-radius:8px;background:var(--color-primary);color:#fff;cursor:pointer;transition:background-color .15s ease,transform .15s ease}.drop-zone:hover{background:#1d4ed8}.drop-zone:active{transform:translateY(1px)}
.drop-zone-active { border-color: var(--color-primary); background: var(--color-primary-soft); }
.drop-zone-disabled { cursor: wait; opacity: .72; }
.file-input { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap; }
.drop-zone-title { font-weight:800; }
.upload-success, .upload-error { margin: 0; padding: .7rem .8rem; border-radius: 8px; font-size: .85rem; }
.upload-success { background: var(--color-success-soft); color: var(--color-success); }
.upload-error { background: var(--color-danger-soft); color: var(--color-danger); }
</style>
