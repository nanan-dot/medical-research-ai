<script setup lang="ts">import { onMounted, onUnmounted, ref } from "vue";
import Breadcrumbs from "./Breadcrumbs.vue";
import ModelPrivacyStatus from "../system/ModelPrivacyStatus.vue";
import { healthApi } from "../../api/health";
const emit = defineEmits<{ openSearch: []; openMenu: [] }>();
const onKey = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); emit("openSearch"); } };
onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));

const hour = new Date().getHours();
const greeting = hour < 6 ? "凌晨好" : hour < 12 ? "上午好" : hour < 18 ? "下午好" : "晚上好";

const systemOk = ref<boolean | null>(null);
onMounted(async () => {
  try { const health = await healthApi.get(); systemOk.value = health.status === "ok" || health.status === "healthy"; }
  catch (cause) { systemOk.value = false; console.warn("系统状态读取失败", cause); }
});
</script>
<template><header class="topbar"><button class="mobile-menu" aria-label="打开导航" @click="emit('openMenu')">☰</button><div class="greeting"><p class="hello">{{ greeting }}，Researcher 👋 <span class="motto">专注医学文献，洞察研究本质</span></p></div><Breadcrumbs class="crumbs"/><div class="tools"><button class="search" @click="emit('openSearch')">⌕ <span>全局搜索</span><kbd>Ctrl K</kbd></button><span class="model-status" :class="systemOk === false ? 'down' : ''"><span class="dot"></span>{{ systemOk === null ? "连接中" : systemOk ? "系统正常" : "连接异常" }}</span><ModelPrivacyStatus/><span class="avatar" aria-label="Researcher 用户头像" title="Researcher">R</span></div></header></template><style scoped>.topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:64px;padding:.55rem 1.4rem;border-bottom:1px solid var(--border-subtle);background:rgba(255,255,255,.9);backdrop-filter:blur(12px)}.greeting{min-width:0}.hello{margin:0;font-size:.95rem;font-weight:700;color:var(--text-primary);white-space:nowrap}.motto{margin-left:.4rem;font-size:.8rem;font-weight:500;color:var(--text-faint)}.crumbs{display:none}.tools{display:flex;align-items:center;gap:.6rem;position:relative}.search{display:inline-flex;align-items:center;gap:.45rem;border:1px solid var(--border-subtle);border-radius:8px;padding:.45rem .7rem;background:var(--surface);color:var(--text-muted);font-size:.82rem;transition:border-color .15s,box-shadow .15s}.search:hover{border-color:var(--color-primary)}.search kbd{font-size:.7rem;color:var(--text-faint)}.model-status{display:inline-flex;align-items:center;gap:.4rem;color:var(--text-muted);font-size:.78rem;white-space:nowrap}.dot{width:.45rem;height:.45rem;border-radius:50%;background:var(--color-success)}.model-status.down .dot{background:var(--color-danger)}.avatar{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--color-primary);color:#fff;font-size:.82rem;font-weight:800}.mobile-menu{display:none}@media(max-width:900px){.mobile-menu{display:block;border:1px solid var(--border-subtle);border-radius:7px;padding:.4rem .6rem;background:var(--surface);color:var(--text-primary)}.greeting{display:none}.crumbs{display:block;min-width:0}.search span{display:none}.search kbd{display:none}.model-status{display:none}}</style>
