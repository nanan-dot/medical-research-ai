<script setup lang="ts">
import type { PaperItem } from "../../api/paperLibrary";
import PaperWorkCard from "./PaperWorkCard.vue";

const props = defineProps<{
  items: readonly PaperItem[]; total: number; selectedId: number | null; loading: boolean; initialized: boolean;
  page: number; pageCount: number; hasPrevious: boolean; hasNext: boolean; density: "comfortable" | "compact";
}>();
const emit = defineEmits<{ select: [id: number]; activate: [paper: PaperItem]; read: [paper: PaperItem]; more: [paper: PaperItem]; previous: []; next: [] }>();

function handleKeys(event: KeyboardEvent): void {
  if (!props.items.length) return;
  const selectedIndex = props.items.findIndex((item) => item.id === props.selectedId);
  const currentIndex = selectedIndex >= 0 ? selectedIndex : 0;
  if (event.key === "ArrowDown") { event.preventDefault(); emit("select", props.items[Math.min(currentIndex + 1, props.items.length - 1)].id); }
  if (event.key === "ArrowUp") { event.preventDefault(); emit("select", props.items[Math.max(currentIndex - 1, 0)].id); }
  if (event.key === "Enter") { event.preventDefault(); emit("activate", props.items[currentIndex]); }
}
</script>

<template>
  <section class="list-wrap" :class="{ compact: density === 'compact' }" aria-label="论文列表">
    <div v-if="loading && !initialized" class="skeletons" aria-label="正在加载论文">
      <div v-for="index in 5" :key="index" class="skeleton"><i></i><span></span><b></b></div>
    </div>
    <div v-else class="paper-list" role="listbox" tabindex="0" aria-label="论文工作列表，使用上下方向键选择，回车进入推荐工作" @keydown="handleKeys">
      <PaperWorkCard v-for="paper in items" :key="paper.id" role="option" :paper="paper" :selected="paper.id === selectedId" @select="emit('select', $event)" @read="emit('read', $event)" @more="emit('more', $event)" />
      <div v-if="initialized && !items.length" class="empty-state">
        <div aria-hidden="true">▤</div><h2>{{ total === 0 ? "论文库还是空的" : "没有符合条件的论文" }}</h2>
        <p>{{ total === 0 ? "从资料库选择论文，或导入一篇新论文开始工作。" : "尝试清除部分筛选条件或调整搜索关键词。" }}</p>
      </div>
    </div>
    <footer v-if="initialized && (items.length || total > 0)" class="pagination">
      <span>共 {{ total }} 条</span>
      <div><button type="button" :disabled="!hasPrevious" aria-label="上一页" @click="emit('previous')">‹</button><b>{{ page }}</b><span>/ {{ pageCount }}</span><button type="button" :disabled="!hasNext" aria-label="下一页" @click="emit('next')">›</button></div>
      <span>每页 5 条</span>
    </footer>
  </section>
</template>

<style scoped>
.list-wrap{min-width:0;background:#fff}.paper-list{outline:0}.paper-list:focus-visible{outline:2px solid #0b5fcc;outline-offset:-2px}.compact :deep(.paper-row){min-height:124px;padding-block:12px}.compact :deep(.activity-line){display:none}.skeletons{background:#fff}.skeleton{display:grid;grid-template-columns:40px minmax(0,1fr) 94px;gap:14px;height:145px;align-items:start;padding:18px;border-bottom:1px solid var(--line)}.skeleton i,.skeleton span,.skeleton b{display:block;border-radius:4px;background:#edf2f7}.skeleton i{width:38px;height:42px}.skeleton span{height:74px}.skeleton b{height:76px}.empty-state{display:grid;min-height:420px;place-items:center;align-content:center;padding:40px;text-align:center}.empty-state>div{display:grid;width:48px;height:48px;place-items:center;border-radius:8px;background:#eaf2ff;color:#0b5fcc;font-size:22px}.empty-state h2{margin:14px 0 5px;font-size:15px}.empty-state p{max-width:330px;margin:0;color:#64748b;font-size:12px;line-height:1.6}.pagination{display:grid;grid-template-columns:1fr auto 1fr;height:48px;align-items:center;padding:0 16px;border-top:1px solid var(--line);color:#64748b;font-size:11.5px;font-variant-numeric:tabular-nums}.pagination>div{display:flex;align-items:center;gap:8px}.pagination>span:last-child{text-align:right}.pagination button{display:grid;width:30px;height:30px;place-items:center;border:1px solid var(--line);border-radius:4px;background:#fff;color:#0b5fcc;font:inherit;font-size:17px}.pagination button:disabled{color:#cbd5e1;cursor:not-allowed}.pagination b{display:grid;width:28px;height:28px;place-items:center;border:1px solid #bdd4f7;border-radius:4px;color:#0b5fcc;font-weight:700}@media(max-width:540px){.pagination{grid-template-columns:1fr auto}.pagination>span:last-child{display:none}.empty-state{min-height:320px;padding:24px}}
</style>
