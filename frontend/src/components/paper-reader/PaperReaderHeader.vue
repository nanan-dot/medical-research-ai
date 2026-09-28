<script setup lang="ts">
import { computed, shallowRef } from "vue";
import type { ReaderBootstrap } from "../../api/paperReader";

const props = defineProps<{
  bootstrap: ReaderBootstrap;
  favoriteBusy: boolean;
  studyEnabled: boolean;
}>();
const emit = defineEmits<{ back: []; favorite: []; study: [] }>();
const menuOpen = shallowRef(false);
const tags = computed(() =>
  [
    props.bootstrap.paper.journal,
    props.bootstrap.paper.year,
    props.bootstrap.paper.paper_type,
  ].filter(Boolean),
);
</script>

<template>
  <header class="reader-header">
    <button type="button" class="back" @click="emit('back')">
      返回论文中心
    </button>
    <div class="paper-meta">
      <h1>{{ bootstrap.paper.title || "未命名论文" }}</h1>
      <p>
        <span v-for="tag in tags" :key="String(tag)">{{ tag }}</span>
      </p>
    </div>
    <div class="header-actions">
      <button
        type="button"
        :aria-pressed="bootstrap.paper.is_favorite"
        :disabled="favoriteBusy"
        @click="emit('favorite')"
      >
        {{ bootstrap.paper.is_favorite ? "已收藏" : "收藏" }}</button
      ><button
        type="button"
        class="study"
        :disabled="!studyEnabled"
        :title="
          studyEnabled ? undefined : '请先从论文库的研究关联中选择研读上下文'
        "
        @click="emit('study')"
      >
        开始研读</button
      ><button
        type="button"
        aria-label="更多阅读操作"
        :aria-expanded="menuOpen"
        aria-controls="reader-more-menu"
        @click="menuOpen = !menuOpen"
      >
        更多
      </button>
      <div v-if="menuOpen" id="reader-more-menu" class="more-menu" role="menu">
        <button type="button" role="menuitem" @click="menuOpen = false">
          复制论文信息
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.reader-header {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr) 455px;
  gap: 0;
  align-items: center;
  min-height: 70px;
  padding: 0;
  border-bottom: 1px solid #e5eaf2;
  background: #fff;
}
.back,
.header-actions button {
  min-height: 36px;
  border: 1px solid #e1e7f0;
  border-radius: 7px;
  background: #fff;
  color: #182235;
  font: inherit;
  font-weight: 700;
}
.back {
  justify-self: start;
  margin-left: 20px;
  padding: 0 10px;
}
.paper-meta { min-width: 0; padding: 0 24px; }
.paper-meta h1 {
  overflow: hidden;
  margin: 0;
  color: #111827;
  font-size: 17px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.paper-meta p {
  display: flex;
  gap: 6px;
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}
.paper-meta p span {
  padding: 2px 6px;
  border-radius: 4px;
  background: #f4f6fa;
}
.header-actions {
  position: relative;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-right: 24px;
}
.header-actions button {
  padding: 0 12px;
}
.header-actions .study {
  border-color: #0868f7;
  background: #0868f7;
  color: #fff;
}
.header-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.more-menu {
  position: absolute;
  z-index: 4;
  right: 0;
  top: 42px;
  width: 150px;
  padding: 4px;
  border: 1px solid #e1e7f0;
  border-radius: 7px;
  background: #fff;
  box-shadow: 0 8px 20px rgb(29 44 69 / 12%);
}
.more-menu button {
  width: 100%;
  border: 0;
  text-align: left;
}
@media (max-width: 767px) {
  .reader-header {
    grid-template-columns: 1fr auto;
    padding: 10px 14px;
  }
  .back {
    grid-column: 1/-1;
    justify-self: start;
  }
  .paper-meta h1 {
    white-space: normal;
  }
  .header-actions button:not(.study) {
    display: none;
  }
}
@media (max-width: 1023px) and (min-width: 768px) {
  .reader-header {
    grid-template-columns: 224px minmax(0, 1fr) auto;
  }
  .paper-meta { padding-inline: 16px; }
  .header-actions { padding-right: 14px; }
  .header-actions button { padding-inline: 9px; }
}
</style>
