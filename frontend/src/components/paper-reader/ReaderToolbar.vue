<script setup lang="ts">
import type { ReaderBootstrap } from "../../api/paperReader";
const props = defineProps<{
  bootstrap: ReaderBootstrap;
  focusMode: boolean;
  currentPage: number;
}>();
const emit = defineEmits<{
  mode: [mode: "original" | "bilingual" | "translated"];
  focus: [];
  page: [page: number];
  zoom: [delta: number];
  fullscreen: [];
}>();
function submitPage(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value);
  if (Number.isInteger(value)) emit("page", value);
}
</script>
<template>
  <section class="toolbar" aria-label="论文阅读工具">
    <div class="toolbar-row">
      <button
        type="button"
        aria-label="打开页面缩略图"
        disabled
        title="缩略图由 PDF 阅读器渲染"
      >
        缩略图</button
      ><button
        type="button"
        aria-label="上一页"
        :disabled="currentPage <= 1"
        @click="emit('page', currentPage - 1)"
      >
        ‹</button
      ><label
        >页码
        <input
          :value="currentPage"
          type="number"
          min="1"
          :max="bootstrap.document.page_count"
          aria-label="跳转页码"
          @change="submitPage"
          @keydown.enter="submitPage" /></label
      ><span>/ {{ bootstrap.document.page_count }}</span
      ><button
        type="button"
        aria-label="下一页"
        :disabled="currentPage >= bootstrap.document.page_count"
        @click="emit('page', currentPage + 1)"
      >
        ›</button
      ><button type="button" aria-label="缩小 PDF" @click="emit('zoom', -0.15)">
        −</button
      ><b>{{ bootstrap.preference.zoom_percent }}%</b
      ><button type="button" aria-label="放大 PDF" @click="emit('zoom', 0.15)">
        ＋</button
      ><button type="button" aria-label="全屏阅读" @click="emit('fullscreen')">
        全屏</button
      ><button type="button" :aria-pressed="focusMode" @click="emit('focus')">
        专注阅读
      </button>
    </div>
    <div class="toolbar-row mode-row" role="tablist" aria-label="阅读模式">
      <button
        role="tab"
        :aria-selected="bootstrap.preference.view_mode === 'original'"
        @click="emit('mode', 'original')"
      >
        原文</button
      ><button
        role="tab"
        :aria-selected="bootstrap.preference.view_mode === 'bilingual'"
        :disabled="bootstrap.capabilities.translation !== 'available'"
        :title="bootstrap.capabilities.translation === 'available' ? '显示原文与中文译文' : '翻译服务当前不可用'"
        @click="emit('mode', 'bilingual')"
      >
        双语</button
      ><button
        role="tab"
        :aria-selected="bootstrap.preference.view_mode === 'translated'"
        :disabled="bootstrap.capabilities.translation !== 'available'"
        :title="bootstrap.capabilities.translation === 'available' ? '显示中文译文' : '翻译服务当前不可用'"
        @click="emit('mode', 'translated')"
      >
        中文</button
      ><span>章节结构已同步到左栏</span>
    </div>
  </section>
</template>
<style scoped>
.toolbar {
  display: grid;
  gap: 10px;
  padding: 12px 18px 10px;
  border-bottom: 1px solid #e5eaf2;
  background: #fff;
}
.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.toolbar button,
.toolbar input {
  min-height: 36px;
  border: 1px solid #dce4f0;
  border-radius: 6px;
  background: #fff;
  color: #25324a;
  font: inherit;
}
.toolbar button {
  padding: 0 11px;
}
.toolbar input {
  width: 52px;
  padding: 0 4px;
}
.toolbar button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.mode-row button[aria-selected="true"] {
  border-color: #0868f7;
  background: #0868f7;
  color: #fff;
}
.mode-row span {
  margin-left: auto;
  color: #0868f7;
  font-size: 12px;
  font-weight: 700;
}
.toolbar button:focus-visible,
.toolbar input:focus-visible { outline: 2px solid #0868f7; outline-offset: 2px; }
@media (max-width: 767px) {
  .toolbar {
    padding-inline: 12px;
  }
  .mode-row span {
    margin-left: 0;
    flex-basis: 100%;
  }
}
</style>
