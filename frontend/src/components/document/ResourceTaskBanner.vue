<script setup lang="ts">
export interface ResourceTaskBannerItem {
  id: number;
  displayName: string;
  taskStatus: string;
  phase: string | null;
  progress: number | null | undefined;
}

const props = defineProps<{ tasks: readonly ResourceTaskBannerItem[]; total: number }>();
const emit = defineEmits<{ openTask: [id: number] }>();
</script>

<template>
  <section v-if="props.tasks.length" class="task-banner" aria-live="polite">
    <div><strong>正在处理 {{ props.tasks[0].displayName }}</strong><span v-if="props.tasks[0].phase"> · {{ props.tasks[0].phase }}</span><span v-if="props.tasks.length > 1"> · 另有 {{ props.tasks.length - 1 }} 项任务</span><progress v-if="props.tasks[0].progress != null" :value="props.tasks[0].progress" max="100">{{ props.tasks[0].progress }}%</progress></div>
    <button type="button" @click="emit('openTask', props.tasks[0].id)">查看进度</button>
  </section>
</template>

<style scoped>
.task-banner { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:48px; padding:8px 14px; border-bottom:1px solid var(--border-subtle); background:var(--color-primary-soft); color:var(--text-primary); font-size:12px; }.task-banner div { display:flex; min-width:0; flex-wrap:wrap; align-items:center; gap:4px; }.task-banner strong { font-size:13px; }.task-banner progress { width:88px; height:5px; margin-left:6px; accent-color:var(--color-primary); }.task-banner button { border:0; background:transparent; color:var(--color-primary); font:inherit; font-weight:700; cursor:pointer; }.task-banner button:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px; }@media(max-width:767px){.task-banner{align-items:flex-start;}.task-banner button{min-height:44px;}}
</style>
