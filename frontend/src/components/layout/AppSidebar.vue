<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { features } from "../../config/features";
import BrandLogo from "../brand/BrandLogo.vue";

defineProps<{ collapsed: boolean }>();
const emit = defineEmits<{ toggle: [] }>();
const route = useRoute();

// 一级导航 = 研究空间分组（恰好 7 项）；底部 = 后台任务 + 设置。
const navItems = computed(() => features.filter((item) => item.showInNavigation && item.group === "研究空间"));
const bottomItems = computed(() => features.filter((item) => item.group === "底部" && item.showInNavigation));
const documentKnowledgeOpen = computed(() => route.path === "/documents" || route.path.startsWith("/documents/") || route.path === "/sources");
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <BrandLogo class="brand-logo" :size="30" />
      <span v-if="!collapsed" class="brand-copy">
        <b class="brand-name">素问</b>
        <span class="brand-sub">医学循证研究平台</span>
      </span>
      <button class="collapse-btn" aria-label="收缩导航" @click="emit('toggle')">‹</button>
    </div>

    <nav class="nav" aria-label="主导航">
      <template v-for="item in navItems" :key="item.id">
        <RouterLink
          :to="item.path"
          class="nav-link"
        >
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
        </RouterLink>
        <nav v-if="!collapsed && documentKnowledgeOpen && item.path === '/documents'" class="subnav" aria-label="文档与知识二级导航">
          <RouterLink to="/sources" class="subnav-link"><span aria-hidden="true">◫</span>知识库</RouterLink>
          <RouterLink to="/documents" class="subnav-link"><span aria-hidden="true">▤</span>文档库</RouterLink>
        </nav>
      </template>
    </nav>

    <nav class="bottom" aria-label="底部导航">
      <RouterLink
        v-for="item in bottomItems"
        :key="item.id"
        :to="item.path"
        class="nav-link"
      >
        <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  width: 216px;
  height: 100vh;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-subtle);
  color: var(--text-primary);
  transition: width 0.2s ease;
  overflow-y: auto;
}
.sidebar.collapsed {
  width: 72px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  height: 72px;
  padding: 0 0.9rem;
  border-bottom: 1px solid var(--border-subtle);
}
.brand-logo {
  flex-shrink: 0;
  color: var(--text-primary);
}
.brand-copy {
  display: grid;
  gap: 0.05rem;
  min-width: 0;
}
.brand-name {
  font-size: 0.95rem;
  font-weight: 800;
  letter-spacing: 0.14em;
}
.brand-sub {
  color: var(--text-faint);
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.collapse-btn {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-size: 1.3rem;
  line-height: 1;
  cursor: pointer;
  padding: 0.2rem 0.3rem;
  border-radius: 6px;
}
.collapse-btn:hover,
.collapse-btn:focus-visible {
  color: var(--color-primary);
  outline: none;
}
.nav {
  display: grid;
  gap: 0.15rem;
  margin-top: 0.7rem;
  padding: 0 0.6rem;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-height: 36px;
  padding: 0.4rem 0.6rem;
  border-radius: 8px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.86rem;
  transition: background-color 0.15s, color 0.15s;
}
.nav-link:hover {
  background: var(--nav-hover-bg);
  color: var(--text-primary);
}
.nav-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}
.nav-link.router-link-active {
  background: var(--nav-active-bg);
  color: var(--nav-active-text);
  font-weight: 700;
}
.nav-icon {
  width: 1.15rem;
  text-align: center;
  flex-shrink: 0;
}
.nav-label {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.subnav {
  display: grid;
  gap: 0.1rem;
  margin: -0.05rem 0 0.25rem 1.55rem;
  padding-left: 0.6rem;
  border-left: 1px solid var(--border-subtle);
}
.subnav-link {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 29px;
  padding: 0.25rem 0.45rem;
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 650;
  text-decoration: none;
}
.subnav-link:hover {
  color: var(--text-primary);
  background: var(--nav-hover-bg);
}
.subnav-link.router-link-active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: 800;
}
.subnav-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}
.bottom {
  display: grid;
  gap: 0.15rem;
  margin-top: 1.2rem;
  padding: 0.7rem 0.6rem 0;
  border-top: 1px solid var(--border-subtle);
}
</style>
