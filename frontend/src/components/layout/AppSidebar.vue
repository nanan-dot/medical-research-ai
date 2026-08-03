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
    <div class="brand"><span class="brand-mark">M</span><span v-if="!collapsed">医学科研智能平台</span><button aria-label="折叠导航" @click="emit('toggle')">‹</button></div>
    <nav class="nav" aria-label="主导航"><template v-for="group in groups" :key="group"><p v-if="!collapsed" class="group">{{ group }}</p><RouterLink v-for="item in grouped(group)" :key="item.id" :to="item.path" class="nav-link"><span>{{ item.icon }}</span><span v-if="!collapsed">{{ item.label }}</span><FeatureStatusBadge v-if="!collapsed && item.status !== 'LIVE'" :status="item.status" /></RouterLink></template></nav>
    <nav class="bottom"><RouterLink v-for="item in bottom" :key="item.id" :to="item.path" class="nav-link"><span>{{ item.icon }}</span><span v-if="!collapsed">{{ item.label }}</span></RouterLink></nav>
  </aside>
</template>

<style scoped>.sidebar{display:flex;flex-direction:column;width:var(--sidebar);min-height:100vh;padding:1rem .7rem;background:var(--navy-950);color:#fff;transition:width .2s}.sidebar.collapsed{width:72px}.brand{display:flex;align-items:center;gap:.55rem;font-size:.9rem;font-weight:800}.brand button{margin-left:auto;border:0;color:#fff;background:transparent;font-size:1.4rem}.brand-mark{display:grid;place-items:center;width:28px;height:28px;background:#3478f6;border-radius:7px}.nav{display:grid;gap:.2rem;margin-top:1.7rem}.group{margin:1rem .45rem .3rem;color:#8eacc7;font-size:.72rem}.nav-link{display:flex;align-items:center;gap:.65rem;min-height:34px;padding:.42rem .5rem;border-radius:7px;color:#d4e2ee;text-decoration:none;font-size:.86rem}.nav-link:hover,.nav-link.router-link-active{color:#fff;background:#194c78}.bottom{display:grid;gap:.2rem;margin-top:auto;padding-top:1rem}</style>
