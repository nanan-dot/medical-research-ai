<script setup lang="ts">
import { computed } from "vue";
import { features } from "../../config/features";
import FeatureStatusBadge from "../system/FeatureStatusBadge.vue";

defineProps<{ collapsed: boolean }>();
const emit = defineEmits<{ toggle: [] }>();
const groups = computed(() => [...new Set(features.filter((item) => item.showInNavigation && item.group !== "底部").map((item) => item.group))]);
const bottom = computed(() => features.filter((item) => item.group === "底部"));
const grouped = (group: string) => features.filter((item) => item.group === group);
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand"><span class="brand-mark">M</span><span v-if="!collapsed" class="brand-name">MedAI · 医学科研智能助手</span><button aria-label="折叠导航" @click="emit('toggle')">‹</button></div>
    <nav class="nav" aria-label="主导航"><template v-for="group in groups" :key="group"><p v-if="!collapsed" class="group">{{ group }}</p><RouterLink v-for="item in grouped(group)" :key="item.id" :to="item.path" class="nav-link"><span class="nav-icon">{{ item.icon }}</span><span v-if="!collapsed" class="nav-label">{{ item.label }}</span><FeatureStatusBadge v-if="!collapsed && item.status !== 'LIVE'" :status="item.status" /></RouterLink></template></nav>
    <nav class="bottom"><RouterLink v-for="item in bottom" :key="item.id" :to="item.path" class="nav-link"><span class="nav-icon">{{ item.icon }}</span><span v-if="!collapsed" class="nav-label">{{ item.label }}</span></RouterLink></nav>
  </aside>
</template>

<style scoped>.sidebar{display:flex;flex-direction:column;width:var(--sidebar);min-height:100vh;background:var(--sidebar-bg);border-right:1px solid var(--border-subtle);color:var(--text-primary);transition:width .2s}.sidebar.collapsed{width:72px}.brand{display:flex;align-items:center;gap:.55rem;height:72px;padding:0 1rem;border-bottom:1px solid var(--border-subtle);font-size:.9rem;font-weight:800}.brand button{margin-left:auto;border:0;color:var(--text-muted);background:transparent;font-size:1.4rem}.brand-mark{display:grid;place-items:center;width:28px;height:28px;border-radius:7px;background:var(--color-primary);color:#fff;font-weight:900}.nav{display:grid;gap:.15rem;margin-top:.6rem;padding:0 .7rem}.group{margin:.95rem .45rem .3rem;color:var(--text-faint);font-size:.7rem;font-weight:700;letter-spacing:.08em}.nav-link{display:flex;align-items:center;gap:.65rem;min-height:34px;padding:.4rem .55rem;border-radius:7px;color:var(--text-muted);text-decoration:none;font-size:.86rem;transition:background-color .15s,color .15s}.nav-link:hover{background:var(--nav-hover-bg);color:var(--text-primary)}.nav-link.router-link-active{background:var(--nav-active-bg);color:var(--nav-active-text);font-weight:700}.nav-icon{width:1.1rem;text-align:center}.bottom{display:grid;gap:.15rem;margin-top:auto;padding:.7rem;border-top:1px solid var(--border-subtle)}</style>
