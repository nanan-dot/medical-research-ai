<script setup lang="ts">
// 顶部栏：左侧项目名 + 项目切换；右侧仅保留搜索与跳转、任务铃铛、账户头像。
// 不含问候语、第二个内容搜索框或系统/模型状态展示。
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { literatureSearchApi } from "../../api/literatureSearch";

const route = useRoute();

// 顶部上下文跟随当前一级工作空间。文献检索的中心、结果、历史页面
// 共用同一份 route meta，因此不会再显示为“工作台”。
const workspaceName = computed(() => {
  const feature = route.meta.feature as { label?: string } | undefined;
  return feature?.label ?? "工作台";
});
const isDocumentDetail = computed(() => /^\/documents\/[^/]+$/.test(route.path));

// 任务铃铛数字：真实进行中（pending/running/failed）任务数。
const activeTaskCount = ref(0);
onMounted(async () => {
  try {
    const page = await literatureSearchApi.listTasks(0, 50);
    activeTaskCount.value = page.items.filter((task) => ["pending", "running", "failed"].includes(task.status)).length;
  } catch {
    activeTaskCount.value = 0;
  }
});

const emit = defineEmits<{ openSearch: []; openMenu: [] }>();
const onKey = (event: KeyboardEvent) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    emit("openSearch");
  }
};
onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <header class="topbar">
    <button class="mobile-menu" aria-label="打开导航" @click="emit('openMenu')">☰</button>
    <nav v-if="isDocumentDetail" class="document-breadcrumb" aria-label="文档详情路径">
      <span>文档与知识</span>
      <span aria-hidden="true">/</span>
      <RouterLink to="/documents">文档库</RouterLink>
      <span aria-hidden="true">/</span>
      <span>文档详情</span>
    </nav>
    <div v-else class="project">
      <span class="project-crumb">{{ workspaceName }}</span>
      <button class="switch-project" aria-label="切换项目">▾</button>
    </div>
    <div class="tools">
      <button class="search" aria-label="搜索与跳转" @click="emit('openSearch')">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <span>搜索与跳转</span>
        <kbd>Ctrl K</kbd>
      </button>
      <button class="bell" :aria-label="`任务通知，${activeTaskCount} 条进行中`" @click="emit('openMenu')">
        <span class="bell-icon" aria-hidden="true">◷</span>
        <span v-if="activeTaskCount > 0" class="bell-badge" aria-hidden="true">{{ activeTaskCount }}</span>
      </button>
      <span class="avatar" aria-label="研究者账户头像" title="研究者">R</span>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 1rem;
  min-height: 64px;
  padding: 0.55rem 1.4rem;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(255, 255, 255, 0.92);
}
.project {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  min-width: 0;
}
.project-crumb {
  color: var(--text-primary);
  font-size: 0.88rem;
  font-weight: 700;
  white-space: nowrap;
}
.document-breadcrumb { display: flex; align-items: center; gap: .45rem; min-width: 0; color: var(--text-muted); font-size: .88rem; white-space: nowrap; }
.document-breadcrumb a { color: var(--color-primary); font-weight: 700; text-decoration: none; }
.document-breadcrumb a:hover, .document-breadcrumb a:focus-visible { text-decoration: underline; outline: none; }
.switch-project {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
  padding: 0.2rem 0.3rem;
  border-radius: 6px;
}
.switch-project:hover,
.switch-project:focus-visible {
  color: var(--color-primary);
  outline: none;
}
.tools {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-left: auto;
}
.search {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 0.45rem 0.7rem;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 0.82rem;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.search:hover,
.search:focus-visible {
  border-color: var(--color-primary);
  outline: none;
}
.search-icon {
  color: var(--text-faint);
}
.search kbd {
  font-size: 0.7rem;
  color: var(--text-faint);
  border: 1px solid var(--border-subtle);
  border-radius: 5px;
  padding: 0.1rem 0.35rem;
  background: var(--surface-muted);
}
.bell {
  position: relative;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 1rem;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.bell:hover,
.bell:focus-visible {
  border-color: var(--color-primary);
  color: var(--color-primary);
  outline: none;
}
.bell-badge {
  position: absolute;
  top: -5px;
  right: -6px;
  display: grid;
  place-items: center;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 99px;
  background: var(--color-danger);
  color: #fff;
  font-size: 0.68rem;
  font-weight: 800;
}
.avatar {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 0.85rem;
  font-weight: 800;
}
.mobile-menu {
  display: none;
}
@media (max-width: 760px) {
  .mobile-menu {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text-primary);
    font-size: 1rem;
    cursor: pointer;
  }
  .project-crumb {
    font-size: 0.8rem;
  }
  .document-breadcrumb { font-size: .8rem; overflow: hidden; text-overflow: ellipsis; }
  .search span:not(.search-icon),
  .search kbd {
    display: none;
  }
}
</style>
