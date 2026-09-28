<script setup lang="ts">
import type { ResourceLibraryStatus, ResourceLibrarySummary } from "../../api/resourceLibrary";

type SummarySelection = "all" | "processed" | "ai_available" | "processing" | "needs_attention";

const props = defineProps<{
  summary: ResourceLibrarySummary | null;
  loading: boolean;
  error?: boolean;
  active: SummarySelection;
}>();
const emit = defineEmits<{ select: [value: SummarySelection] }>();
const cards: ReadonlyArray<{ key: SummarySelection; label: string; note: string; icon: string; tone: string; title: string; status: ResourceLibraryStatus | null; value: (summary: ResourceLibrarySummary) => number }> = [
  { key: "all", label: "资料总量", note: "全部导入资料", icon: "▰", tone: "neutral", status: null, title: "全库已纳入资料的去重总量。", value: (summary) => summary.total },
  { key: "processed", label: "已处理", note: "解析内容已完成", icon: "✓", tone: "success", status: "needs_processing", title: "内容提取已完成；该项与 AI 可使用存在包含关系。", value: (summary) => summary.processed },
  { key: "ai_available", label: "AI 可使用", note: "可用于搜索、问答", icon: "AI", tone: "violet", status: "ai_available", title: "解析和索引完成，可用于检索与问答。", value: (summary) => summary.ai_available },
  { key: "processing", label: "处理中", note: "正在解析或建立索引", icon: "◌", tone: "info", status: "processing", title: "正在解析或建立索引的资料。", value: (summary) => summary.processing },
  { key: "needs_attention", label: "异常", note: "需要处理", icon: "!", tone: "warning", status: "needs_attention", title: "失败、失效或内容已更新，需要用户处理。", value: (summary) => summary.needs_attention },
];
</script>

<template>
  <section class="summary" aria-label="资料库全局统计" aria-live="polite">
    <button v-for="card in cards" :key="card.key" type="button" class="card" :class="[`card--${card.tone}`, { 'is-active': props.active === card.key }]" :aria-pressed="props.active === card.key" :title="card.title" @click="emit('select', card.key)">
      <span class="icon" aria-hidden="true">{{ card.icon }}</span>
      <span class="card-copy"><small class="card-label">{{ card.label }}</small><strong v-if="!props.loading && props.summary">{{ card.value(props.summary) }}</strong><strong v-else-if="props.error" class="unavailable">暂不可用</strong><strong v-else class="skeleton">&nbsp;</strong><small class="card-note">{{ card.note }}</small></span>
    </button>
  </section>
</template>

<style scoped>
.summary { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:16px; margin:0 0 10px; }
.card { display:flex; align-items:center; gap:14px; min-width:0; min-height:92px; padding:14px 16px; border:1px solid var(--border-subtle); border-radius:10px; background:var(--surface); box-shadow:0 1px 3px rgb(15 23 42 / 4%); color:var(--text-primary); font:inherit; text-align:left; cursor:pointer; transition:border-color 140ms ease,box-shadow 140ms ease,transform 140ms ease; }.card:hover { border-color:color-mix(in srgb,var(--color-primary) 35%,var(--border-subtle)); box-shadow:0 8px 20px rgb(15 23 42 / 7%); transform:translateY(-1px); }.card:focus-visible { outline:3px solid var(--color-primary-soft); outline-offset:2px; }.card.is-active { border-color:var(--color-primary); box-shadow:0 0 0 2px var(--color-primary-soft); }.icon { display:grid; width:48px; height:48px; flex:0 0 auto; place-items:center; border-radius:50%; background:var(--color-primary-soft); color:var(--color-primary); font-size:16px; font-weight:800; letter-spacing:-.04em; }.card--success .icon{background:var(--color-success-soft);color:var(--color-success)}.card--warning .icon{background:var(--color-warning-soft);color:var(--color-warning)}.card--info .icon{background:var(--color-primary-soft);color:var(--color-primary)}.card--violet .icon{background:#f1e9ff;color:#7047df}.card-copy{display:grid;min-width:0;gap:2px}.card-label,.card-note,strong{display:block}.card-label{color:var(--text-muted);font-size:12px;font-weight:700}.card-note{overflow:hidden;margin-top:1px;color:var(--text-muted);font-size:12px;line-height:1.25;text-overflow:ellipsis;white-space:nowrap}strong{font-size:21px;line-height:1.15;font-variant-numeric:tabular-nums}.skeleton{width:42px;height:22px;border-radius:4px;background:var(--surface-muted)}.unavailable{font-size:13px;color:var(--text-muted)}@media(max-width:1023px){.summary{display:flex;gap:12px;overflow-x:auto;padding:1px;scroll-snap-type:x mandatory}.card{min-width:190px;scroll-snap-align:start}}@media(max-width:767px){.summary{margin:0 0 12px}.card{min-height:86px;min-width:178px;padding:10px 12px}.icon{width:42px;height:42px;font-size:14px}}@media(prefers-reduced-motion:reduce){.card{transition:none}.card:hover{transform:none}}
</style>
