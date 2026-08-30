<script setup lang="ts">
import { nextTick, onBeforeUnmount, shallowRef, useId, useTemplateRef, watch } from "vue";

const props = defineProps<{ strategyId: number; archived: boolean; disabled?: boolean }>();
const emit = defineEmits<{ action: [action: "rename" | "move" | "clone" | "archive" | "restore", id: number] }>();
const isOpen = shallowRef(false);
const triggerRef = useTemplateRef<HTMLButtonElement>("trigger");
const menuRef = useTemplateRef<HTMLElement>("menu");
const menuId = `strategy-actions-${useId()}`;
function close(restoreFocus = false) { isOpen.value = false; if (restoreFocus) void nextTick(() => triggerRef.value?.focus()); }
function onDocumentPointerDown(event: PointerEvent) { const target = event.target as Node; if (!menuRef.value?.contains(target) && !triggerRef.value?.contains(target)) close(); }
function choose(action: "rename" | "move" | "clone" | "archive" | "restore") { close(true); emit("action", action, props.strategyId); }
function onKeydown(event: KeyboardEvent) { if (event.key === "Escape") { event.preventDefault(); close(true); } }
watch(isOpen, (open) => { document.removeEventListener("pointerdown", onDocumentPointerDown); if (open) document.addEventListener("pointerdown", onDocumentPointerDown); });
onBeforeUnmount(() => document.removeEventListener("pointerdown", onDocumentPointerDown));
</script>

<template>
  <div class="menu-wrap" @keydown="onKeydown">
    <button ref="trigger" class="more" type="button" aria-label="更多策略操作" :aria-expanded="isOpen" :aria-controls="menuId" aria-haspopup="menu" :disabled="props.disabled" @click="isOpen = !isOpen">•••</button>
    <div v-if="isOpen" :id="menuId" ref="menu" class="menu" role="menu" aria-label="策略管理操作">
      <template v-if="props.archived"><button type="button" role="menuitem" @click="choose('restore')">恢复策略</button></template>
      <template v-else>
        <button type="button" role="menuitem" @click="choose('rename')">重命名</button>
        <button type="button" role="menuitem" @click="choose('move')">移动到项目</button>
        <button type="button" role="menuitem" @click="choose('clone')">创建副本</button>
        <button type="button" role="menuitem" class="archive" @click="choose('archive')">归档策略</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.menu-wrap { position:relative; }.more { width:34px; min-height:31px; padding:0; border:1px solid var(--border-subtle); border-radius:6px; background:var(--surface); color:var(--text-primary); font:700 16px/1 inherit; cursor:pointer; }.menu { position:absolute; z-index:20; top:calc(100% + 4px); right:0; display:grid; min-width:136px; padding:5px; border:1px solid var(--border-subtle); border-radius:7px; background:var(--surface); box-shadow:var(--shadow-md); }.menu button { min-height:30px; border:0; border-radius:4px; background:transparent; color:var(--text-primary); font:600 12px/1 inherit; text-align:left; cursor:pointer; }.menu button:hover,.menu button:focus-visible { background:var(--surface-muted); outline:0; }.menu .archive { color:var(--color-danger); }.more:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px; }
</style>
