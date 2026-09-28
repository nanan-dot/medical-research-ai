<script setup lang="ts">
import { computed, shallowRef, watch } from "vue";
import { useRoute } from "vue-router";
import { features } from "../../config/features";
import type { FeatureDefinition } from "../../types/feature";
import BrandLogo from "../brand/BrandLogo.vue";
import BaseIcon from "../ui/BaseIcon.vue";

defineProps<{ collapsed: boolean }>();
const emit = defineEmits<{ toggle: [] }>();
const route = useRoute();

const featureById = new Map(features.map((feature) => [feature.id, feature]));
function navFeature(id: string): FeatureDefinition {
  const feature = featureById.get(id);
  if (!feature) throw new Error(`Missing sidebar feature: ${id}`);
  return feature;
}
const workbench = navFeature("workbench");
const literature = navFeature("literature");
const resources = navFeature("documents");
const paperResearch = navFeature("paper-research");
const primaryItems = [navFeature("comparison"), navFeature("directions"), navFeature("writing")];
const literatureActive = computed(() => route.path.startsWith("/literature-search") || route.path === "/recommendations");
const resourcesActive = computed(() => ["/sources", "/papers", "/notes", "/documents"].some((path) => route.path === path || route.path.startsWith(`${path}/`)));
const literatureCurrentPath = computed(() => route.path === "/recommendations"
  ? "/recommendations"
  : route.path.startsWith("/literature-search/history")
    ? "/literature-search/history"
    : route.path.startsWith("/literature-search/results")
      ? "/literature-search/results"
      : "/literature-search");
const literatureExpanded = shallowRef(literatureActive.value);
const resourcesExpanded = shallowRef(resourcesActive.value);
const paperResearchActive = computed(() => route.path.startsWith("/paper-research") || route.path === "/paper-center");
const paperResearchExpanded = shallowRef(true);
watch(() => route.path, () => {
  if (literatureActive.value) literatureExpanded.value = true;
  if (resourcesActive.value) resourcesExpanded.value = true;
  if (paperResearchActive.value) paperResearchExpanded.value = true;
});
const bottomItems = computed(() =>
  features.filter((item) => item.group === "底部" && item.showInNavigation),
);
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <BrandLogo class="brand-logo" :size="38" />
      <span v-if="!collapsed" class="brand-copy">
        <b class="brand-name">素问</b>
        <span class="brand-sub">医学循证研究平台</span>
      </span>
      <button
        class="collapse-btn"
        :aria-label="collapsed ? '展开导航' : '收缩导航'"
        :title="collapsed ? '展开导航' : '收缩导航'"
        @click="emit('toggle')"
      >
        {{ collapsed ? "›" : "‹" }}
      </button>
    </div>

    <nav class="nav" aria-label="主导航">
      <RouterLink :to="workbench.path" class="nav-link" :aria-label="collapsed ? workbench.label : undefined" :title="collapsed ? workbench.label : undefined" :data-tooltip="collapsed ? workbench.label : undefined"><span class="nav-icon" aria-hidden="true">{{ workbench.icon }}</span><span v-if="!collapsed" class="nav-label">{{ workbench.label }}</span></RouterLink>

      <section class="nav-group">
        <div class="nav-group-heading">
          <RouterLink :to="literature.path" class="nav-link" :class="{ 'group-active': literatureActive }" :aria-label="collapsed ? literature.label : undefined" :title="collapsed ? literature.label : undefined" :data-tooltip="collapsed ? literature.label : undefined"><span class="nav-icon" aria-hidden="true">{{ literature.icon }}</span><span v-if="!collapsed" class="nav-label">{{ literature.label }}</span></RouterLink>
          <button v-if="!collapsed" class="subnav-toggle" type="button" :aria-expanded="literatureExpanded" aria-controls="literature-subnav" :aria-label="literatureExpanded ? '收起文献检索二级导航' : '展开文献检索二级导航'" @click="literatureExpanded = !literatureExpanded"><span aria-hidden="true">⌃</span></button>
        </div>
        <nav v-if="!collapsed && literatureExpanded" id="literature-subnav" class="subnav" aria-label="文献检索二级导航">
          <RouterLink to="/literature-search" class="subnav-link" :class="{ active: literatureCurrentPath === '/literature-search' }" :aria-current="literatureCurrentPath === '/literature-search' ? 'page' : undefined"><BaseIcon class="subnav-icon" name="search" />检索中心</RouterLink>
          <RouterLink to="/literature-search/results" class="subnav-link" :class="{ active: literatureCurrentPath === '/literature-search/results' }" :aria-current="literatureCurrentPath === '/literature-search/results' ? 'page' : undefined"><BaseIcon class="subnav-icon" name="document" />检索结果</RouterLink>
          <RouterLink to="/recommendations" class="subnav-link" :class="{ active: literatureCurrentPath === '/recommendations' }" :aria-current="literatureCurrentPath === '/recommendations' ? 'page' : undefined"><BaseIcon class="subnav-icon" name="star" />文献推荐</RouterLink>
          <RouterLink to="/literature-search/history" class="subnav-link" :class="{ active: literatureCurrentPath === '/literature-search/history' }" :aria-current="literatureCurrentPath === '/literature-search/history' ? 'page' : undefined"><BaseIcon class="subnav-icon" name="sync" />检索历史</RouterLink>
        </nav>
      </section>

      <section class="nav-group">
        <div class="nav-group-heading">
          <RouterLink :to="resources.path" class="nav-link" :class="{ 'group-active': resourcesActive }" :aria-label="collapsed ? resources.label : undefined" :title="collapsed ? resources.label : undefined" :data-tooltip="collapsed ? resources.label : undefined"><span class="nav-icon" aria-hidden="true">{{ resources.icon }}</span><span v-if="!collapsed" class="nav-label">{{ resources.label }}</span></RouterLink>
          <button v-if="!collapsed" class="subnav-toggle" type="button" :aria-expanded="resourcesExpanded" aria-controls="resource-subnav" :aria-label="resourcesExpanded ? '收起研究资源二级导航' : '展开研究资源二级导航'" @click="resourcesExpanded = !resourcesExpanded"><span aria-hidden="true">⌃</span></button>
        </div>
        <nav v-if="!collapsed && resourcesExpanded" id="resource-subnav" class="subnav" aria-label="研究资源二级导航">
          <RouterLink to="/sources" class="subnav-link"><span class="subnav-icon" aria-hidden="true">◫</span>知识库</RouterLink>
          <RouterLink to="/papers" class="subnav-link"><span class="subnav-icon" aria-hidden="true">▤</span>论文库</RouterLink>
          <RouterLink to="/notes" class="subnav-link"><span class="subnav-icon" aria-hidden="true">▥</span>笔记库</RouterLink>
          <RouterLink to="/documents" class="subnav-link"><span class="subnav-icon" aria-hidden="true">▤</span>资料库</RouterLink>
        </nav>
      </section>

      <section class="nav-group">
        <div class="nav-group-heading">
          <RouterLink :to="paperResearch.path" class="nav-link" :class="{ 'group-active': paperResearchActive }" :aria-label="collapsed ? paperResearch.label : undefined" :title="collapsed ? paperResearch.label : undefined" :data-tooltip="collapsed ? paperResearch.label : undefined"><span class="nav-icon" aria-hidden="true">{{ paperResearch.icon }}</span><span v-if="!collapsed" class="nav-label">{{ paperResearch.label }}</span></RouterLink>
          <button v-if="!collapsed" class="subnav-toggle" type="button" :aria-expanded="paperResearchExpanded" aria-controls="paper-research-subnav" :aria-label="paperResearchExpanded ? '收起论文研究二级导航' : '展开论文研究二级导航'" @click="paperResearchExpanded = !paperResearchExpanded"><span aria-hidden="true">⌃</span></button>
        </div>
        <nav v-if="!collapsed && paperResearchExpanded" id="paper-research-subnav" class="subnav" aria-label="论文研究二级导航">
          <RouterLink to="/paper-center" class="subnav-link" :class="{ active: route.path === '/paper-center' }" :aria-current="route.path === '/paper-center' ? 'page' : undefined"><BaseIcon class="subnav-icon" name="document" />论文中心</RouterLink>
          <RouterLink to="/paper-research" class="subnav-link" :class="{ active: route.path === '/paper-research' }" :aria-current="route.path === '/paper-research' ? 'page' : undefined"><BaseIcon class="subnav-icon" name="document" />论文阅读</RouterLink>
        </nav>
      </section>

      <RouterLink v-for="item in primaryItems" :key="item.id" :to="item.path" class="nav-link" :aria-label="collapsed ? item.label : undefined" :title="collapsed ? item.label : undefined" :data-tooltip="collapsed ? item.label : undefined"><span class="nav-icon" aria-hidden="true">{{ item.icon }}</span><span v-if="!collapsed" class="nav-label">{{ item.label }}</span></RouterLink>
    </nav>

    <nav class="bottom" aria-label="底部导航">
      <RouterLink
        v-for="item in bottomItems"
        :key="item.id"
        :to="item.path"
        class="nav-link"
        :aria-label="collapsed ? item.label : undefined"
        :title="collapsed ? item.label : undefined"
        :data-tooltip="collapsed ? item.label : undefined"
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
  width: var(--app-sidebar-expanded-width, 220px);
  height: 100vh;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-subtle);
  color: var(--text-primary);
  transition: width 0.2s ease;
  overflow-y: auto;
}
.sidebar.collapsed {
  width: var(--app-sidebar-collapsed-width, 64px);
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  height: 76px;
  padding: 0 1.25rem;
  border-bottom: 1px solid var(--border-subtle);
}
.brand-logo {
  flex-shrink: 0;
  color: var(--color-primary);
}
.note-brand-mark {
  display: grid;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(145deg, #2b7cff, #0b5ee8);
  box-shadow: 0 5px 12px rgb(18 104 234 / 22%);
  color: #fff;
  font-size: 21px;
  font-weight: 800;
}
.brand-copy {
  display: grid;
  gap: 0.05rem;
  min-width: 0;
}
.brand-name {
  font-size: 1.25rem;
  font-weight: 800;
  letter-spacing: 0.14em;
}
.brand-sub {
  color: var(--text-faint);
  font-size: 0.72rem;
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
  align-content: start;
  gap: 0;
  margin-top: 0.7rem;
  padding: 0 0.95rem;
}
.nav-section {
  display: grid;
  gap: 0.1rem;
  margin: 0;
}
.nav-section + .nav-section {
  margin-top: 0.55rem;
}
.nav-section-title {
  margin: 0.7rem 0.55rem 0.25rem;
  color: var(--text-primary);
  font-size: 0.75rem;
  font-weight: 800;
  line-height: 1.3;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-height: 40px;
  padding: 0.45rem 0.65rem;
  border-radius: 9px;
  color: var(--text-primary);
  text-decoration: none;
  font-size: 0.86rem;
  transition:
    background-color 0.15s,
    color 0.15s;
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
  background: #e7f0ff;
  color: var(--nav-active-text);
  font-weight: 700;
}
.nav-group-heading {
  display: flex;
  align-items: center;
  min-width: 0;
}
.nav-group-heading .nav-link {
  flex: 1;
  min-width: 0;
}
.nav-group-heading .group-active {
  color: var(--text-primary);
}
.subnav-toggle {
  display: grid;
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  margin-right: 0.35rem;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
  transition:
    transform 0.15s ease,
    background-color 0.15s ease;
}
.subnav-toggle:hover,
.subnav-toggle:focus-visible {
  background: var(--nav-hover-bg);
  outline: none;
}
.subnav-toggle[aria-expanded="false"] {
  transform: rotate(180deg);
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
  margin: 0 0 0.3rem 24px;
  padding: 0;
}
.subnav-link {
  display: grid;
  grid-template-columns: 1.15rem minmax(0, 1fr);
  align-items: center;
  gap: 0.45rem;
  min-height: 30px;
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 650;
  text-decoration: none;
}
.subnav-icon {
  flex: 0 0 auto;
  width: 1.15rem;
  height: 1.15rem;
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
.subnav-link.active {
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
  margin-top: auto;
  padding: 0.75rem 0.65rem 0.9rem;
  border-top: 1px solid var(--border-subtle);
}
.note-reference-nav {
  display: grid;
  gap: 2px;
  padding: 17px 15px;
}
.note-reference-nav h2 {
  margin: 14px 8px 5px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 800;
}
.note-reference-link {
  display: flex;
  min-height: 40px;
  align-items: center;
  gap: 12px;
  padding: 7px 9px;
  border-radius: 9px;
  color: var(--text-primary);
  font-size: 14px;
  text-decoration: none;
}
.note-reference-link > span {
  width: 18px;
  color: #4c607d;
  text-align: center;
}
.note-reference-link:hover,
.note-reference-link:focus-visible {
  background: var(--nav-hover-bg);
  outline: none;
}
.note-reference-link.router-link-active {
  background: #e8f1ff;
  color: var(--color-primary);
  font-weight: 750;
}
.note-reference-link.router-link-active > span {
  color: var(--color-primary);
}
.note-user {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: 10px;
  align-items: center;
  margin-top: auto;
  padding: 14px 16px 17px;
  border-top: 1px solid var(--border-subtle);
}
.note-user-avatar {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 50%;
  background: #15899a;
  color: #fff;
  font-weight: 800;
}
.note-user > span:nth-child(2) {
  display: grid;
  gap: 3px;
}
.note-user b { font-size: 13px; }
.note-user small { color: var(--text-faint); font-size: 11px; }
.notes-context .collapse-btn { display: none; }
.sidebar.collapsed .brand {
  gap: 0.2rem;
  justify-content: flex-start;
  padding-inline: 0.35rem;
}
.sidebar.collapsed .collapse-btn {
  margin-left: auto;
  padding-inline: 0.15rem;
}
.sidebar.collapsed .brand-logo {
  width: 32px;
  height: 32px;
}
.sidebar.collapsed .nav,
.sidebar.collapsed .bottom {
  padding-inline: 0.5rem;
}
.sidebar.collapsed .nav-section + .nav-section {
  margin-top: 0.15rem;
}
.sidebar.collapsed .nav-link {
  position: relative;
  justify-content: center;
  min-height: 44px;
  padding: 0.5rem;
}
.sidebar.collapsed .nav-icon {
  width: 1.4rem;
  color: currentColor;
  font-size: 1.05rem;
}
.sidebar.collapsed .nav-link[data-tooltip]::after {
  position: absolute;
  z-index: 20;
  left: calc(100% + 0.65rem);
  top: 50%;
  display: block;
  width: max-content;
  max-width: 13rem;
  padding: 0.42rem 0.58rem;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--sidebar-bg);
  box-shadow: 0 8px 18px rgb(15 42 80 / 0.14);
  color: var(--text-primary);
  content: attr(data-tooltip);
  font-size: 0.78rem;
  font-weight: 650;
  line-height: 1.2;
  opacity: 0;
  pointer-events: none;
  transform: translate(-0.25rem, -50%);
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
  white-space: nowrap;
}
.sidebar.collapsed .nav-link[data-tooltip]:hover::after,
.sidebar.collapsed .nav-link[data-tooltip]:focus-visible::after {
  opacity: 1;
  transform: translate(0, -50%);
}
@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .sidebar.collapsed .nav-link[data-tooltip]::after {
    transition: none;
  }
}
</style>
