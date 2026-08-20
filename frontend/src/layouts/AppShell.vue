<script setup lang="ts">
import { computed, provide, shallowRef } from "vue";
import { useRoute } from "vue-router";

import AppSidebar from "../components/layout/AppSidebar.vue";
import AppTopbar from "../components/layout/AppTopbar.vue";
import GlobalSearchDialog from "../components/layout/GlobalSearchDialog.vue";
import MobileNavigation from "../components/layout/MobileNavigation.vue";
import DocumentKnowledgeWorkspaceHeader from "../components/document-knowledge/DocumentKnowledgeWorkspaceHeader.vue";

const collapsed = shallowRef(false);
const searchOpen = shallowRef(false);
const mobileOpen = shallowRef(false);
const route = useRoute();
const documentKnowledgePage = computed(() => {
  if (route.path === "/sources") {
    return { active: "sources" as const, description: "让本地研究材料成为可追溯的证据资产。" };
  }
  return null;
});

function openSearch(): void {
  searchOpen.value = true;
}

provide<() => void>("openSearch", openSearch);
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <div class="shell">
    <AppSidebar :collapsed="collapsed" @toggle="collapsed = !collapsed" />
    <div class="work">
      <AppTopbar @open-search="openSearch" @open-menu="mobileOpen = true" />
      <main id="main-content" class="content" tabindex="-1">
        <div v-if="documentKnowledgePage" class="document-knowledge-shell">
          <DocumentKnowledgeWorkspaceHeader
            :active="documentKnowledgePage.active"
            :description="documentKnowledgePage.description"
          />
        </div>
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in"><component :is="Component" /></Transition>
        </RouterView>
      </main>
    </div>
    <MobileNavigation :open="mobileOpen" @close="mobileOpen = false" />
    <GlobalSearchDialog v-model="searchOpen" />
  </div>
</template>

<style scoped>
.skip-link { position: fixed; z-index: 100; top: .5rem; left: .5rem; transform: translateY(-200%); padding: .65rem .8rem; border-radius: 6px; background: var(--color-primary); color: #fff; font-weight: 800; text-decoration: none; }
.skip-link:focus { transform: translateY(0); }
.shell { display: grid; grid-template-columns: auto minmax(0, 1fr); min-height: 100vh; background: var(--page-bg); }
.work { min-width: 0; }
.content { min-height: calc(100vh - var(--topbar-height)); }
.document-knowledge-shell { width: min(100% - 3rem, 1440px); margin: 0 auto; padding-top: 1.5rem; }
.page-enter-active, .page-leave-active { transition: opacity .18s ease, transform .18s ease; }
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; transform: translateY(-4px); }
@media (max-width: 900px) { .shell { display: block; }.shell > :first-child { display: none; } }
</style>
