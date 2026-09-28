<script setup lang="ts">
import { computed, nextTick, shallowRef, useTemplateRef, watch } from "vue";

import type { PaperAddRequest } from "../../api/paperLibrary";
import BaseIcon from "../ui/BaseIcon.vue";

const props = defineProps<{ open: boolean; pending: boolean; error: string | null }>();
const emit = defineEmits<{ close: []; submit: [payload: PaperAddRequest]; upload: [] }>();
const doi = shallowRef("");
const pmid = shallowRef("");
const doiInput = useTemplateRef<HTMLInputElement>("doiInput");
let priorFocus: HTMLElement | null = null;
const hasIdentity = computed(() => Boolean(doi.value.trim() || pmid.value.trim()));

function close(): void { if (!props.pending) emit("close"); }
function submit(): void {
  if (!hasIdentity.value) return;
  emit("submit", { ...(doi.value.trim() ? { doi: doi.value.trim() } : {}), ...(pmid.value.trim() ? { pmid: pmid.value.trim() } : {}) });
}
function chooseUpload(): void { if (!props.pending) emit("upload"); }

watch(() => props.open, async (isOpen) => {
  if (isOpen) { priorFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null; await nextTick(); doiInput.value?.focus(); }
  else { priorFocus?.focus(); doi.value = ""; pmid.value = ""; }
});
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-layer" @click.self="close">
      <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="add-paper-title" @keydown.esc.prevent="close">
        <header><div><h2 id="add-paper-title">导入新论文</h2><p>上传 PDF，或用 DOI / PMID 建立可核验的论文记录。</p></div><button type="button" aria-label="关闭导入论文" :disabled="pending" @click="close"><BaseIcon name="close" /></button></header>
        <button class="upload-option" type="button" :disabled="pending" @click="chooseUpload"><BaseIcon name="document" /><span><b>上传 PDF</b><small>复用资料库导入与后台处理流程</small></span><span>›</span></button>
        <div class="divider"><span>或使用文献标识符</span></div>
        <form @submit.prevent="submit">
          <label for="paper-doi">DOI</label><input id="paper-doi" ref="doiInput" v-model="doi" autocomplete="off" placeholder="10.1056/NEJMoa…" />
          <label for="paper-pmid">PMID</label><input id="paper-pmid" v-model="pmid" inputmode="numeric" autocomplete="off" placeholder="例如 32970396" />
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <footer><button type="button" :disabled="pending" @click="close">取消</button><button class="submit" type="submit" :disabled="pending || !hasIdentity">{{ pending ? "正在添加…" : "添加论文" }}</button></footer>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-layer{position:fixed;z-index:60;inset:0;display:grid;place-items:center;padding:16px;background:rgb(15 23 42 / 30%)}.dialog{width:min(470px,100%);padding:20px;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 14px 42px rgb(15 23 42 / 16%)}header{display:flex;justify-content:space-between;gap:16px}h2{margin:0;font-size:18px}header p{margin:5px 0 0;color:#64748b;font-size:12px;line-height:1.5}header>button{display:grid;width:32px;height:32px;place-items:center;border:0;background:transparent;color:#475569}header :deep(.icon){width:18px}.upload-option{display:grid;grid-template-columns:36px minmax(0,1fr) auto;width:100%;align-items:center;gap:10px;margin-top:20px;border:1px solid #c9ddfb;border-radius:6px;padding:12px;background:#f7faff;color:#0b5fcc;text-align:left}.upload-option>:deep(.icon){width:23px;height:23px}.upload-option>span:nth-child(2){display:grid;gap:2px}.upload-option b{color:#0f172a;font-size:13px}.upload-option small{color:#64748b;font-size:11px}.divider{display:flex;align-items:center;gap:10px;margin:17px 0;color:#94a3b8;font-size:10.5px}.divider::before,.divider::after{height:1px;flex:1;background:var(--line);content:""}form{display:grid;gap:7px}form label{margin-top:5px;color:#334155;font-size:12px;font-weight:700}form input{height:38px;border:1px solid var(--line);border-radius:5px;padding:0 10px;color:#0f172a;font:inherit;font-size:12.5px}.error{margin:5px 0 0;color:#c52b2f;font-size:12px}footer{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}footer button{height:36px;border:1px solid var(--line);border-radius:4px;padding:0 13px;background:#fff;color:#334155;font:inherit;font-size:12px;font-weight:700}.submit{border-color:#0b5fcc;background:#0b5fcc;color:#fff}button:disabled{cursor:not-allowed;opacity:.5}@media(max-width:540px){.dialog-layer{align-items:end;padding:0}.dialog{border-radius:10px 10px 0 0;padding:18px}}
</style>
