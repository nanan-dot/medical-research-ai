<script setup lang="ts">
import { nextTick, shallowRef, useTemplateRef } from "vue";

import BaseIcon from "../ui/BaseIcon.vue";

defineProps<{ query: string; loading: boolean }>();
const emit = defineEmits<{ search: [value: string]; addFromLibrary: []; importPaper: []; openFilters: [] }>();
const menuOpen = shallowRef(false);
const menu = useTemplateRef<HTMLElement>("menu");

async function toggleMenu(): Promise<void> {
  menuOpen.value = !menuOpen.value;
  if (menuOpen.value) { await nextTick(); menu.value?.querySelector<HTMLElement>("button")?.focus(); }
}

function choose(action: "library" | "import"): void {
  menuOpen.value = false;
  if (action === "library") emit("addFromLibrary"); else emit("importPaper");
}

function closeOnFocusOut(event: FocusEvent): void {
  if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) menuOpen.value = false;
}
</script>

<template>
  <header class="library-header">
    <div class="heading"><h1>论文库</h1><p>集中管理科研论文，追踪阅读、分析与研究使用状态</p></div>
    <label class="library-search">
      <BaseIcon name="search" />
      <input :value="query" type="search" autocomplete="off" placeholder="搜索标题、作者、期刊、DOI、PMID、关键词…" :aria-busy="loading" @input="emit('search', ($event.target as HTMLInputElement).value)" />
      <kbd>⌘ K</kbd>
    </label>
    <div class="header-actions">
      <button class="filter-button" type="button" @click="emit('openFilters')"><BaseIcon name="filter" /><span>筛选</span></button>
      <div class="add-wrap" @focusout="closeOnFocusOut">
        <button class="add-button" type="button" aria-haspopup="menu" :aria-expanded="menuOpen" @click="toggleMenu"><BaseIcon name="plus" /><span>添加论文</span><BaseIcon name="chevron-down" /></button>
        <div v-if="menuOpen" ref="menu" class="add-menu" role="menu" @keydown.esc="menuOpen = false">
          <button type="button" role="menuitem" @click="choose('library')"><BaseIcon name="folder" /><span><b>从资料库选择</b><small>把已有论文资料加入工作体系</small></span></button>
          <button type="button" role="menuitem" @click="choose('import')"><BaseIcon name="plus" /><span><b>导入新论文</b><small>上传 PDF，或使用 DOI、PMID</small></span></button>
        </div>
      </div>
      <button class="notification" type="button" aria-label="任务通知">◷</button>
      <span class="researcher-avatar" aria-label="研究者账户">R</span>
    </div>
  </header>
</template>

<style scoped>
.library-header{display:grid;grid-template-columns:448px 490px minmax(0,1fr);height:80px;align-items:center;gap:18px;padding:0 20px 0 28px;border-bottom:1px solid var(--line);background:#fff}.heading{min-width:0}.heading h1{margin:0;color:var(--ink-900);font-size:23px;font-weight:780;letter-spacing:-.035em;line-height:1.15}.heading p{overflow:hidden;margin:5px 0 0;color:#52627a;font-size:12.5px;text-overflow:ellipsis;white-space:nowrap}.library-search{display:flex;height:39px;align-items:center;gap:10px;border:1px solid #d5deea;border-radius:6px;padding:0 11px;background:#fff;color:#64748b}.library-search :deep(.icon){flex:0 0 auto;width:17px;height:17px}.library-search input{min-width:0;width:100%;border:0;outline:0;background:transparent;color:#0f172a;font:inherit;font-size:12.5px}.library-search kbd{border:1px solid #e2e8f0;border-radius:5px;padding:1px 6px;background:#f8fafc;color:#64748b;font-size:10px;white-space:nowrap}.header-actions{display:flex;align-items:center;justify-content:flex-end;gap:20px}.add-wrap{position:relative}.add-button,.filter-button{display:inline-flex;height:40px;align-items:center;justify-content:center;gap:9px;border-radius:5px;padding:0 16px;font:inherit;font-size:13px;font-weight:700}.add-button{border:1px solid #0b5fcc;background:#0b5fcc;color:#fff;min-width:158px}.add-button :deep(.icon:first-child){width:17px;height:17px}.add-button :deep(.icon:last-child){width:12px;height:12px;margin-left:5px}.filter-button{display:none;border:1px solid var(--line);background:#fff;color:#334155}.add-menu{position:absolute;z-index:55;top:calc(100% + 7px);right:0;width:258px;padding:6px;border:1px solid var(--line);border-radius:7px;background:#fff;box-shadow:0 10px 28px rgb(15 23 42 / 12%)}.add-menu button{display:flex;width:100%;align-items:flex-start;gap:10px;border:0;border-radius:5px;padding:10px;background:#fff;color:#0f172a;text-align:left}.add-menu button:hover,.add-menu button:focus-visible{background:#f3f7ff;outline:none}.add-menu :deep(.icon){width:17px;height:17px;margin-top:2px;color:#0b5fcc}.add-menu span{display:grid;gap:2px}.add-menu b{font-size:12.5px}.add-menu small{color:#64748b;font-size:10.5px}.notification{display:grid;width:36px;height:36px;place-items:center;border:1px solid var(--line);border-radius:50%;background:#fff;color:#334155;font-size:16px}.researcher-avatar{display:grid;width:34px;height:34px;place-items:center;border-radius:50%;background:#173a6a;color:#fff;font-size:12px;font-weight:800}
@media(max-width:1279px){.library-header{grid-template-columns:minmax(230px,.8fr) minmax(300px,1fr) auto;padding-inline:20px}.filter-button{display:inline-flex}.notification{display:none}.heading p{max-width:250px}.add-button{min-width:132px;padding-inline:12px}}
@media(max-width:900px){.library-header{grid-template-columns:minmax(0,1fr) auto;height:auto;min-height:80px;padding:13px 16px}.library-search{grid-column:1/-1;grid-row:2}.heading p{max-width:none}.researcher-avatar{display:none}.filter-button span,.add-button>span{display:none}.filter-button,.add-button{width:40px;min-width:40px;padding:0}.add-button :deep(.icon:last-child){display:none}}
@media(max-width:520px){.heading h1{font-size:21px}.heading p{font-size:11px}.library-search kbd{display:none}.header-actions{gap:7px}}
</style>
