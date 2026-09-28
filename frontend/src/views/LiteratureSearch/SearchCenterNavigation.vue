<script setup lang="ts">
import { shallowRef, useTemplateRef } from "vue";
import { RouterLink } from "vue-router";
const menu = useTemplateRef<HTMLDetailsElement>("menu");
const isOpen = shallowRef(false);
const destinations = [
  { path: "/literature-search", label: "检索中心" },
  { path: "/literature-search/results", label: "检索结果" },
  { path: "/recommendations", label: "文献推荐" },
  { path: "/literature-search/history", label: "检索历史" },
  { path: "/sources", label: "知识库" },
];
function close(): void { if (menu.value) menu.value.open = false; }
function closeWithFocus(): void { close(); menu.value?.querySelector("summary")?.focus(); }
</script>

<template>
  <details
    ref="menu"
    class="center-navigation"
    @toggle="isOpen = menu?.open ?? false"
    @keydown.esc.prevent="closeWithFocus"
  >
    <summary
      role="button"
      aria-label="打开导航"
    >
      ☰
    </summary>
    <nav
      v-if="isOpen"
      aria-label="检索中心导航"
    >
      <RouterLink
        v-for="destination in destinations"
        :key="destination.path"
        :to="destination.path"
        @click="close"
      >
        {{ destination.label }}
      </RouterLink>
    </nav>
  </details>
</template>

<style scoped>
/* 仅补齐本页的导航入口：共享侧栏与顶栏按钮的断点间存在 761–900px 空档。 */
.center-navigation { display: none; position: relative; }
.center-navigation summary { display: grid; place-items: center; width: 36px; height: 36px; list-style: none; border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--surface); color: var(--text-primary); cursor: pointer; }
.center-navigation summary::-webkit-details-marker { display: none; }
.center-navigation nav { position: absolute; top: 44px; left: 0; z-index: 40; display: grid; width: 170px; padding: 8px; border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--surface); box-shadow: var(--shadow-md); }
.center-navigation a { padding: 9px 12px; color: var(--text-primary); text-decoration: none; border-radius: 6px; }
.center-navigation a:hover { background: var(--accent-soft); }
.center-navigation summary:focus-visible, .center-navigation a:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
@media (min-width: 761px) and (max-width: 900px) { .center-navigation { display: block; } }
</style>
