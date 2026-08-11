<script setup lang="ts">
import { shallowRef } from "vue";
import type { IndexedPaper } from "../../api/paperResearch";
const props = defineProps<{ papers: readonly IndexedPaper[]; loading: boolean; error: string | null }>();
const emit = defineEmits<{ search: [query: string]; select: [paper: IndexedPaper] }>();
const query = shallowRef("");
function submit(): void { emit("search", query.value); }
</script>
<template>
  <section class="picker" aria-labelledby="indexed-paper-title">
    <h2 id="indexed-paper-title">继续你的论文研究</h2>
    <p class="copy">从已完成索引的论文中选择一篇，开始或继续单篇精读。</p>
    <form class="search" @submit.prevent="submit"><label for="indexed-paper-query">搜索已索引论文</label><div><input id="indexed-paper-query" v-model="query" placeholder="按论文标题、文件名或 PMID 搜索" /><button type="submit">搜索</button></div></form>
    <p v-if="props.error" class="error" role="alert">{{ props.error }} 请重试。</p><p v-else-if="props.loading" role="status" class="state">正在加载已索引论文…</p>
    <p v-else-if="props.papers.length === 0" class="state">暂无已索引论文。请先在文档与知识库完成解析和索引。</p>
    <ul v-else class="paper-list"><li v-for="paper in props.papers" :key="paper.document_id"><button type="button" @click="emit('select', paper)"><span><strong>{{ paper.title }}</strong><small v-if="paper.year || paper.pmid">{{ paper.year ?? "年份未提供" }}<template v-if="paper.pmid"> · PMID {{ paper.pmid }}</template></small></span><span class="action">开始单篇精读</span></button></li></ul>
  </section>
</template>
<style scoped>
.picker{display:grid;gap:.8rem;padding:1.25rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--surface)}.picker h2{margin:0;font-size:1.25rem}.copy,.state{margin:0;color:var(--text-muted)}.search{display:grid;gap:.35rem;font-size:.85rem;font-weight:700}.search div{display:flex;gap:.5rem}.search input{flex:1;min-width:0;padding:.6rem .7rem;border:1px solid var(--border-strong);border-radius:7px;background:var(--surface)}.search button,.paper-list button{font:inherit;cursor:pointer}.search button{border:1px solid var(--color-primary);border-radius:7px;padding:.6rem .8rem;background:var(--color-primary);color:#fff}.error{margin:0;color:var(--color-danger)}.paper-list{display:grid;gap:.35rem;margin:0;padding:0;list-style:none}.paper-list button{display:flex;justify-content:space-between;gap:1rem;width:100%;padding:.75rem 0;border:0;border-top:1px solid var(--border-subtle);background:transparent;color:var(--text-primary);text-align:left}.paper-list strong,.paper-list small{display:block;overflow-wrap:anywhere}.paper-list small{margin-top:.2rem;color:var(--text-muted);font-size:.8rem}.action{flex:none;color:var(--color-primary);font-size:.85rem;font-weight:700}.paper-list button:hover .action,.paper-list button:focus-visible .action{text-decoration:underline}@media(max-width:640px){.search div,.paper-list button{flex-direction:column}.action{align-self:flex-start}}
</style>
