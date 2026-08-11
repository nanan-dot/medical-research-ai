<script setup lang="ts">
import type { PaperResearchOverview } from "../../api/paperResearch";
type OverviewRead = { readonly [K in keyof PaperResearchOverview]: readonly PaperResearchOverview[K][number][] };
const props = defineProps<{ overview: OverviewRead; loading: boolean; error: string | null }>();
const emit = defineEmits<{ read: [documentId: number]; chat: [conversationId: number, documentId: number | null] }>();
function date(value: string): string { return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
</script>
<template>
 <section class="streams" aria-label="最近研究活动"><p v-if="props.error" class="error" role="alert">{{ props.error }} 请刷新页面后重试。</p><p v-else-if="props.loading" class="state" role="status">正在加载最近研究活动…</p><template v-else>
  <section class="stream"><h2>最近精读</h2><p v-if="!props.overview.recent_analyses.length" class="state">选择一篇已索引论文，即可在此继续精读。</p><ul v-else><li v-for="item in props.overview.recent_analyses" :key="item.analysis_id"><div><strong>{{ item.title }}</strong><small>最近更新：{{ date(item.updated_at) }}</small></div><button type="button" @click="emit('read', item.document_id)">继续精读</button></li></ul></section>
  <section class="stream"><h2>最近证据问答</h2><p v-if="!props.overview.recent_conversations.length" class="state">从单篇精读进入证据问答后，最近会话会显示在这里。</p><ul v-else><li v-for="item in props.overview.recent_conversations" :key="item.id"><div><strong>{{ item.title || "未命名证据问答" }}</strong><small>最近更新：{{ date(item.updated_at) }}</small></div><button type="button" @click="emit('chat', item.id, item.document_ids.length === 1 ? item.document_ids[0] : null)">恢复会话</button></li></ul></section>
 </template></section>
</template>
<style scoped>.streams{display:grid;gap:1rem}.stream{padding:1.1rem 0;border-top:1px solid var(--border-subtle)}.stream h2{margin:0 0 .65rem;font-size:1.15rem}.stream ul{display:grid;gap:.45rem;margin:0;padding:0;list-style:none}.stream li{display:flex;justify-content:space-between;gap:1rem;padding:.65rem 0;border-top:1px solid var(--border-subtle)}.stream strong,.stream small{display:block;overflow-wrap:anywhere}.stream small,.state{color:var(--text-muted);font-size:.82rem}.state,.error{margin:0}.error{color:var(--color-danger)}.stream button{align-self:center;border:0;background:transparent;color:var(--color-primary);font:inherit;font-weight:700;white-space:nowrap;cursor:pointer}@media(max-width:640px){.stream li{flex-direction:column}.stream button{align-self:start}}</style>
