<script setup lang="ts">
import { computed, shallowRef } from "vue";
import type { ReaderBootstrap } from "../../api/paperReader";
const props = defineProps<{ bootstrap: ReaderBootstrap; collapsed: boolean }>();
const emit = defineEmits<{ toggle: []; page: [page: number] }>();
const progressWidth = computed(
  () => `${Math.min(100, Math.max(0, props.bootstrap.progress.percent))}%`,
);
const activeMode = shallowRef<"outline" | "history">("outline");
const query = shallowRef("");
const currentLocationVisible = computed(() => {
  const value = query.value.trim().toLocaleLowerCase();
  return (
    !value ||
    "当前阅读位置".includes(value) ||
    String(props.bootstrap.resume.page).includes(value)
  );
});
const visibleOutline = computed(() => {
  const value = query.value.trim().toLocaleLowerCase();
  return props.bootstrap.outline.filter((section) =>
    !value || section.title.toLocaleLowerCase().includes(value),
  );
});
</script>
<template>
  <aside class="left-rail" :class="{ collapsed }" aria-label="阅读导航">
    <template v-if="!collapsed"
      ><section class="progress-section">
        <div class="section-heading"><h2>阅读进度</h2><b>{{ bootstrap.progress.percent }}%</b></div>
        <div class="track" aria-label="阅读进度">
          <i :style="{ width: progressWidth }"></i>
        </div>
        <p>{{ bootstrap.progress.qualified_pages }} / {{ bootstrap.progress.total_pages }} 页</p>
      </section>
      <section>
        <div class="tabs" role="tablist" aria-label="阅读导航视图">
          <button
            role="tab"
            :aria-selected="activeMode === 'outline'"
            @click="activeMode = 'outline'"
          >
            论文结构
          </button>
          <button
            role="tab"
            :aria-selected="activeMode === 'history'"
            @click="activeMode = 'history'"
          >
            阅读历史
          </button>
        </div>
        <label
          ><span class="sr-only">搜索论文结构</span
          ><input
            v-model="query"
            type="search"
            :placeholder="
              activeMode === 'outline' ? '搜索论文结构' : '搜索阅读历史'
            "
        /></label>
        <div v-if="activeMode === 'outline'" class="navigation-content">
          <template v-if="bootstrap.capabilities.outline === 'available'">
            <button
              v-for="section in visibleOutline"
              :key="section.id"
              type="button"
              class="outline-item"
              :style="{ paddingInlineStart: `${10 + Math.min(section.level, 4) * 10}px` }"
              @click="emit('page', section.first_page)"
            >
              <span>{{ section.title }}</span><b>第 {{ section.first_page }} 页</b>
            </button>
            <p v-if="!visibleOutline.length" class="outline-empty">没有匹配的章节</p>
          </template>
          <p v-else class="muted">论文结构处理中，仍可按页阅读。</p>
        </div>
        <div v-else class="navigation-content">
          <button
            v-if="currentLocationVisible"
            type="button"
            class="history-item"
          >
            <span>当前阅读位置</span><b>第 {{ bootstrap.resume.page }} 页</b>
          </button>
          <p v-else class="muted">没有匹配的阅读记录。</p>
        </div>
      </section></template
    ><button
      type="button"
      class="collapse"
      :aria-label="collapsed ? '展开阅读导航' : '收起阅读导航'"
      @click="emit('toggle')"
    >
      {{ collapsed ? "›" : "‹ 收起侧栏" }}
    </button>
  </aside>
</template>
<style scoped>
.left-rail {
  display: flex;
  flex-direction: column;
  min-width: 230px;
  border-right: 1px solid #e5eaf2;
  background: #f9fbff;
}
.left-rail section {
  flex: none;
  padding: 14px 14px;
  border-bottom: 1px solid #e5eaf2;
}
.section-heading { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
.section-heading h2 { margin:0; }
.section-heading b { color:#1769e8; font-size:15px; }
.left-rail h2 {
  margin: 0 0 8px;
  font-size: 14px;
}
.left-rail b {
  font-size: 18px;
}
.track {
  height: 4px;
  margin-top: 7px;
  border-radius: 4px;
  background: #dfe8f5;
}
.track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #0868f7;
}
.left-rail p {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}
.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}
.tabs button,
.collapse,
input {
  min-height: 36px;
  border: 1px solid #dce4f0;
  border-radius: 6px;
  background: #fff;
  color: #344054;
  font: inherit;
}
.tabs button[aria-selected="true"] {
  border-color: #0868f7;
  color: #0868f7;
}
.left-rail label {
  display: block;
  margin-top: 10px;
}
.left-rail input {
  box-sizing: border-box;
  width: 100%;
  padding: 0 9px;
}
.navigation-content {
  margin-top: 9px;
}
.outline-empty { margin:8px 0 0; padding:10px; border:1px dashed #cdd9ea; border-radius:6px; color:#8492a6!important; text-align:center; }
.history-item {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  border: 0;
  border-radius: 7px;
  padding: 0 9px;
  background: #edf4ff;
  color: #1769e8;
  font: inherit;
  text-align: left;
}
.outline-item { display:flex; width:100%; min-height:34px; align-items:center; justify-content:space-between; gap:8px; border:0; border-left:2px solid transparent; padding:6px 8px; background:transparent; color:#344054; font:inherit; font-size:12px; text-align:left; }
.outline-item:hover { background:#f0f5ff; color:#1769e8; }
.outline-item span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.outline-item b { flex:none; color:#7b8799; font-size:10px; font-weight:600; }
.history-item b {
  font-size: 11px;
}
.collapse {
  margin: 14px 14px 14px;
  text-align: left;
  padding: 0 8px;
  margin-top: auto;
}
.collapsed {
  min-width: 46px;
}
.collapsed .collapse {
  display: grid;
  width: 32px;
  place-items: center;
  margin: 14px auto;
  padding: 0;
  text-align: center;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
</style>
