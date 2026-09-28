<script setup lang="ts">
import { computed, provide, shallowRef } from "vue";
import { useRoute } from "vue-router";

import AppSidebar from "../components/layout/AppSidebar.vue";
import AppTopbar from "../components/layout/AppTopbar.vue";
import GlobalSearchDialog from "../components/layout/GlobalSearchDialog.vue";
import MobileNavigation from "../components/layout/MobileNavigation.vue";

const collapsed = shallowRef(false);
const searchOpen = shallowRef(false);
const mobileOpen = shallowRef(false);
const route = useRoute();
// 工作台的参考布局将标题栏并入策略页本身。桌面端仅对该深链隐藏
// 通用 Topbar；小屏仍保留它以提供打开导航的可访问入口。
// 检索中心本身就是完整策略工作台，使用页面专属标题栏；保留 workspace
// 深链的同一表现，避免根路由出现两个顶栏。
const isStrategyWorkspace = computed(
  () =>
    route.path === "/literature-search" ||
    route.path === "/literature-search/workspace" ||
    route.path === "/recommendations" ||
    route.path === "/literature-search/history" ||
    route.path === "/paper-center",
);
const isReaderWorkspace = computed(
  () => route.path === "/paper-research" || route.path.startsWith("/paper-research/"),
);

function openSearch(): void {
  searchOpen.value = true;
}

provide<() => void>("openSearch", openSearch);
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <div class="shell" :class="{ 'reader-shell': isReaderWorkspace }">
    <AppSidebar v-if="!isReaderWorkspace" class="app-sidebar" :collapsed="collapsed" @toggle="collapsed = !collapsed" />
    <div class="work">
      <AppTopbar v-if="!isReaderWorkspace"
        :class="{ 'workspace-topbar': isStrategyWorkspace }"
        @open-search="openSearch"
        @open-menu="mobileOpen = true"
      />
      <main
        id="main-content"
        class="content"
        :class="{ 'workspace-content': isStrategyWorkspace, 'reader-content': isReaderWorkspace }"
        tabindex="-1"
      >
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
    <MobileNavigation :open="mobileOpen" @close="mobileOpen = false" />
    <GlobalSearchDialog v-model="searchOpen" />
  </div>
</template>

<style scoped>
.skip-link {
  position: fixed;
  z-index: 100;
  top: 0.5rem;
  left: 0.5rem;
  transform: translateY(-200%);
  padding: 0.65rem 0.8rem;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
  text-decoration: none;
}
.skip-link:focus {
  transform: translateY(0);
}
.shell {
  --app-sidebar-expanded-width: 230px;
  --app-sidebar-collapsed-width: 64px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  min-height: 100vh;
  background: var(--page-bg);
}
.work {
  min-width: 0;
}
.content {
  min-height: calc(100vh - var(--topbar-height));
}
:deep(.workspace-topbar) {
  display: none;
}
.workspace-content {
  min-height: 100vh;
}
.reader-shell { display: block; }
.reader-content { min-height: 100vh; }
.page-enter-active,
.page-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
@media (max-width: 900px) {
  .shell {
    display: block;
  }
  .shell:not(.reader-shell) > .app-sidebar {
    display: none;
  }
  :deep(.workspace-topbar) {
    display: flex;
  }
}
</style>
