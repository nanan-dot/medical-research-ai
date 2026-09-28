<script setup lang="ts">
import { nextTick, shallowRef, watch } from "vue";

import { DEFAULT_RESOURCE_LIBRARY_FILTERS, resourceLibraryApi, type ResourceLibraryItem } from "../../api/resourceLibrary";
import BaseIcon from "../ui/BaseIcon.vue";

const props = defineProps<{ open: boolean; pending: boolean; error: string | null }>();
const emit = defineEmits<{ close: []; select: [documentId: number] }>();
const query = shallowRef("");
const items = shallowRef<ResourceLibraryItem[]>([]);
const loading = shallowRef(false);
const loadError = shallowRef<string | null>(null);
const selectedId = shallowRef<number | null>(null);
let controller: AbortController | null = null;
let timer: ReturnType<typeof setTimeout> | null = null;

async function load(): Promise<void> {
  controller?.abort(); controller = new AbortController(); loading.value = true; loadError.value = null;
  try { const page = await resourceLibraryApi.items({ ...DEFAULT_RESOURCE_LIBRARY_FILTERS, query: query.value, fileTypes: ["pdf"] }, 0, 30, controller.signal); items.value = page.items; }
  catch (cause) { if (!(cause instanceof DOMException && cause.name === "AbortError")) loadError.value = cause instanceof Error ? cause.message : "资料暂时无法加载"; }
  finally { loading.value = false; }
}

function search(): void { if (timer) clearTimeout(timer); timer = setTimeout(() => void load(), 250); }
function close(): void { if (!props.pending) emit("close"); }
function submit(): void { if (selectedId.value) emit("select", selectedId.value); }

watch(() => props.open, async (open) => { if (open) { selectedId.value = null; await load(); await nextTick(); } else { controller?.abort(); } });
</script>

<template>
  <Teleport to="body"><div v-if="open" class="picker-layer" @click.self="close"><section class="picker" role="dialog" aria-modal="true" aria-labelledby="picker-title" @keydown.esc.prevent="close"><header><div><h2 id="picker-title">从资料库选择</h2><p>只展示资料库中的 PDF；加入论文库不会复制原文件。</p></div><button type="button" aria-label="关闭资料选择" @click="close"><BaseIcon name="close" /></button></header><label class="picker-search"><BaseIcon name="search" /><input v-model="query" type="search" placeholder="搜索资料名称或路径…" @input="search" /></label><div class="picker-list" :aria-busy="loading"><p v-if="loading" class="state">正在读取资料…</p><p v-else-if="loadError" class="state error" role="alert">{{ loadError }} <button type="button" @click="load">重试</button></p><label v-for="item in items" v-else :key="item.id" :class="{ selected: selectedId === item.id }"><input v-model="selectedId" type="radio" :value="item.id" /><span class="pdf">PDF</span><span><b>{{ item.display_name }}</b><small>{{ item.source_name }} · {{ item.relative_path }}</small></span></label><p v-if="!loading && !loadError && !items.length" class="state">资料库中没有符合条件的 PDF。</p></div><p v-if="error" class="submit-error" role="alert">{{ error }}</p><footer><button type="button" :disabled="pending" @click="close">取消</button><button class="submit" type="button" :disabled="pending || !selectedId" @click="submit">{{ pending ? "正在加入…" : "加入论文库" }}</button></footer></section></div></Teleport>
</template>

<style scoped>
.picker-layer{position:fixed;z-index:60;inset:0;display:grid;place-items:center;padding:16px;background:rgb(15 23 42 / 30%)}.picker{width:min(620px,100%);max-height:min(720px,90vh);display:flex;flex-direction:column;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 14px 42px rgb(15 23 42 / 16%)}header{display:flex;justify-content:space-between;gap:16px;padding:19px 20px 14px;border-bottom:1px solid var(--line)}h2{margin:0;font-size:18px}header p{margin:4px 0 0;color:#64748b;font-size:12px}header button{display:grid;width:32px;height:32px;place-items:center;border:0;background:transparent;color:#475569}header :deep(.icon){width:18px}.picker-search{display:flex;height:38px;flex:0 0 auto;align-items:center;gap:8px;margin:14px 16px;border:1px solid var(--line);border-radius:5px;padding:0 10px;color:#64748b}.picker-search :deep(.icon){width:15px}.picker-search input{min-width:0;width:100%;border:0;outline:0;font:inherit;font-size:12.5px}.picker-list{min-height:260px;overflow:auto;border-block:1px solid var(--line)}.picker-list>label{display:grid;grid-template-columns:18px 38px minmax(0,1fr);align-items:center;gap:10px;padding:11px 16px;border-bottom:1px solid #edf1f6;cursor:pointer}.picker-list>label.selected{background:#f3f7ff}.picker-list input{accent-color:#0b5fcc}.picker-list label>span:last-child{display:grid;min-width:0;gap:2px}.picker-list b,.picker-list small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.picker-list b{font-size:12.5px}.picker-list small{color:#64748b;font-size:10.5px}.pdf{display:grid;width:32px;height:34px;place-items:center;border-radius:4px;background:#fff0f0;color:#ef3340;font-size:9px;font-weight:800}.state{margin:60px 20px;color:#64748b;text-align:center}.state button{border:0;background:transparent;color:#0b5fcc;text-decoration:underline}.error,.submit-error{color:#c52b2f}.submit-error{margin:10px 16px 0;font-size:12px}footer{display:flex;justify-content:flex-end;gap:8px;padding:14px 16px}footer button{height:36px;border:1px solid var(--line);border-radius:4px;padding:0 13px;background:#fff;color:#334155;font:inherit;font-size:12px;font-weight:700}.submit{border-color:#0b5fcc;background:#0b5fcc;color:#fff}button:disabled{cursor:not-allowed;opacity:.5}@media(max-width:540px){.picker-layer{align-items:end;padding:0}.picker{max-height:90vh;border-radius:10px 10px 0 0}}
</style>
