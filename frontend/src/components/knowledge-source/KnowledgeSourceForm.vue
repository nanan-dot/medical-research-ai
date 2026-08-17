<script setup lang="ts">
import { nextTick, reactive, shallowRef } from "vue";

import {
  knowledgeSourcesApi,
  type CreateKnowledgeSource,
  type KnowledgeSourceType,
} from "../../api/knowledgeSources";

defineProps<{ disabled: boolean }>();
const emit = defineEmits<{ submit: [payload: CreateKnowledgeSource] }>();

const form = reactive<CreateKnowledgeSource>({
  name: "",
  source_type: "local_folder",
  root_path: "",
});

const sourceTypes: ReadonlyArray<{ value: KnowledgeSourceType; label: string }> = [
  { value: "local_folder", label: "本地文件夹" },
  { value: "obsidian_vault", label: "Obsidian Vault" },
  { value: "temporary_import", label: "临时导入目录" },
];

const browseError = shallowRef<string | null>(null);
const isBrowsing = shallowRef(false);

function submit(): void {
  emit("submit", { ...form });
}

function folderName(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).at(-1) ?? "";
}

async function browseDirectory(): Promise<void> {
  browseError.value = null;
  isBrowsing.value = true;
  // 先让 Vue 渲染选择状态，再调用会阻塞等待原生窗口关闭的本地接口。
  await nextTick();
  try {
    const { path } = await knowledgeSourcesApi.browseDirectory();
    if (!path) return;
    form.root_path = path;
    if (!form.name.trim()) form.name = folderName(path);
  } catch {
    browseError.value = "无法打开系统文件夹选择器。请确认后端正在本机桌面会话中运行后重试。";
  } finally {
    isBrowsing.value = false;
  }
}
</script>

<template>
  <form class="source-form" @submit.prevent="submit">
    <section class="form-intro" aria-labelledby="directory-title">
      <p class="form-kicker">资料来源</p>
      <h4 id="directory-title">选择要长期同步的资料文件夹</h4>
      <p>系统只会扫描你确认的目录。后续将文件放入该目录后，可在知识库中手动同步。</p>
    </section>

    <div class="field-grid">
      <label class="field">
        <span class="field-label">知识库名称</span>
        <input v-model.trim="form.name" required maxlength="200" placeholder="选择文件夹后自动填入">
      </label>
      <label class="field">
        <span class="field-label">资料类型</span>
        <select v-model="form.source_type">
          <option v-for="type in sourceTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
      </label>
    </div>

    <section class="directory-card" :class="{ selected: Boolean(form.root_path) }" aria-labelledby="directory-label">
      <div class="directory-copy">
        <span id="directory-label" class="field-label">授权目录</span>
        <strong>{{ form.root_path ? "已选择资料文件夹" : "尚未选择文件夹" }}</strong>
        <p>{{ form.root_path || "点击右侧“选择文件夹”打开 Windows 文件夹选择器" }}</p>
      </div>
      <button class="browse-action" type="button" :disabled="disabled || isBrowsing" @click="browseDirectory">
        {{ isBrowsing ? "正在打开…" : form.root_path ? "重新选择" : "选择文件夹" }}
      </button>
    </section>

    <p v-if="isBrowsing" class="picker-state" role="status">系统文件夹选择器已打开，请在窗口中选中目标目录后点击“选择文件夹”。</p>
    <p v-if="browseError" class="browse-error" role="alert">{{ browseError }}</p>

    <footer class="form-footer">
      <span>目录确认后才会保存为知识库来源。</span>
      <button class="primary-action" type="submit" :disabled="disabled || !form.root_path">添加知识源</button>
    </footer>
  </form>
</template>

<style scoped>
.source-form { display:grid; gap:16px; }
.form-intro { padding:12px 0; border-bottom:1px solid var(--border-subtle); }
.form-intro p,.directory-copy p,.picker-state,.browse-error,.form-footer span { margin:0; color:var(--text-muted); font-size:.8rem; line-height:1.55; }
.form-kicker { color:var(--color-primary)!important; font-size:.7rem!important; font-weight:800; letter-spacing:.08em; }
.form-intro h4 { margin:4px 0; color:var(--ink-900,var(--text-primary)); font-size:1rem; }
.field-grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(184px,.72fr); gap:12px; }
.field { display:grid; gap:6px; min-width:0; }
.field-label { color:var(--text-muted); font-size:.76rem; font-weight:750; }
.field input,.field select { box-sizing:border-box; width:100%; min-height:40px; border:1px solid var(--border-strong); border-radius:8px; padding:8px 10px; background:var(--surface); color:var(--text-primary); font:inherit; font-size:.86rem; }
.field select { cursor:pointer; }
.field input:focus-visible,.field select:focus-visible,.browse-action:focus-visible,.primary-action:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px; }
.directory-card { display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:84px; padding:12px; border:1px dashed var(--border-strong); border-radius:8px; background:var(--surface-muted); }
.directory-card.selected { border-style:solid; border-color:var(--color-primary); background:var(--color-primary-soft); }
.directory-copy { display:grid; gap:2px; min-width:0; }
.directory-copy strong { color:var(--ink-900,var(--text-primary)); font-size:.86rem; }
.directory-copy p { overflow:hidden; font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:.76rem; text-overflow:ellipsis; white-space:nowrap; }
.browse-action,.primary-action { min-height:40px; border-radius:8px; padding:8px 12px; font:inherit; font-size:.82rem; font-weight:750; white-space:nowrap; cursor:pointer; }
.browse-action { flex:0 0 auto; border:1px solid var(--border-strong); background:var(--surface); color:var(--text-primary); }
.primary-action { border:0; background:var(--color-primary); color:#fff; }
.browse-action:disabled,.primary-action:disabled { cursor:not-allowed; opacity:.55; }
.picker-state { padding:8px 10px; border-left:2px solid var(--color-primary); background:var(--color-primary-soft); }
.browse-error { padding:8px 10px; border-left:2px solid var(--color-danger); background:var(--color-danger-soft); color:var(--color-danger); }
.form-footer { display:flex; align-items:center; justify-content:space-between; gap:12px; padding-top:12px; border-top:1px solid var(--border-subtle); }
@media (max-width:560px) { .field-grid { grid-template-columns:1fr; }.directory-card,.form-footer { align-items:stretch; flex-direction:column; }.browse-action,.primary-action { width:100%; }.directory-copy p { white-space:normal; overflow-wrap:anywhere; } }
</style>
