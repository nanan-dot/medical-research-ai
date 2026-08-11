<script setup lang="ts">
import { computed, shallowRef } from "vue";
import type { KnowledgeSource } from "../../api/knowledgeSources";

const props = defineProps<{ sources: readonly KnowledgeSource[]; loading: boolean }>();
const emit = defineEmits<{ search: [query: string, knowledgeSourceId: number | null, indexedOnly: boolean] }>();
const query = shallowRef("");
const sourceId = shallowRef<number | null>(null);
const indexedOnly = shallowRef(true);
const canSubmit = computed(() => Boolean(query.value.trim()) && !props.loading);
function submit(): void { if (canSubmit.value) emit("search", query.value.trim(), sourceId.value, indexedOnly.value); }
</script>

<template>
  <form class="navigation-panel" @submit.prevent="submit">
    <div class="heading"><div><h2>AI 资料导航</h2><p>仅检索当前本地资料的真实解析内容；结果均附来源和定位。</p></div><span>本地资料</span></div>
    <label class="query-label" for="navigation-query">检索问题</label>
    <textarea id="navigation-query" v-model="query" rows="3" maxlength="500" placeholder="例如：找出讨论耐药机制、且已经完成索引的论文" />
    <div class="controls"><label>知识源 <select v-model="sourceId"><option :value="null">全部知识源</option><option v-for="source in sources" :key="source.id" :value="source.id">{{ source.name }}</option></select></label><label class="check"><input v-model="indexedOnly" type="checkbox" /> 仅已索引文档</label><button type="submit" :disabled="!canSubmit">{{ loading ? "正在检索" : "检索资料" }}</button></div>
  </form>
</template>

<style scoped>
.navigation-panel{display:grid;gap:.7rem;padding:1rem 1.1rem;border:1px solid #bfdbfe;border-radius:10px;background:#f8fbff}.heading,.controls{display:flex;align-items:center;justify-content:space-between;gap:.75rem}.heading h2,.heading p{margin:0}.heading h2{font-size:1.15rem}.heading p{margin-top:.25rem;color:var(--text-muted);font-size:.85rem}.heading span{padding:.25rem .5rem;border-radius:999px;background:#dbeafe;color:#1d4ed8;font-size:.75rem}.query-label{font-weight:700}.navigation-panel textarea,.navigation-panel select{box-sizing:border-box;border:1px solid var(--border-strong);border-radius:6px;background:#fff;color:var(--text-primary);font:inherit}.navigation-panel textarea{width:100%;padding:.6rem}.controls label{display:flex;align-items:center;gap:.4rem;color:var(--text-secondary);font-size:.85rem}.controls select{padding:.4rem}.controls button{padding:.5rem .8rem;border:0;border-radius:6px;background:var(--color-primary);color:#fff;font:inherit;font-weight:700}.controls button:disabled{opacity:.55}@media(max-width:760px){.heading,.controls{align-items:stretch;flex-direction:column}.controls button{width:100%}}
</style>
