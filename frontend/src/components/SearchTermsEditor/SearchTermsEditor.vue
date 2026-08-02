<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import type { BuiltQuery, ExpandedTerms, SearchTermGroup } from "../../api/literatureSearch";

interface Props { expanded: ExpandedTerms; result: BuiltQuery | null; loading: boolean; }
const props = defineProps<Props>();
const emit = defineEmits<{ build: [groups: SearchTermGroup[]] }>();
function clone(groups: SearchTermGroup[]) { return groups.map((group) => ({ ...group, terms: [...group.terms] })); }
const groups = reactive<SearchTermGroup[]>(clone(props.expanded.term_groups));
watch(() => props.expanded, (next) => { groups.splice(0, groups.length, ...clone(next.term_groups)); }, { deep: true });
const visibleGroups = computed(() => groups.filter((group) => group.terms.length > 0));
function updateTerms(group: SearchTermGroup, value: string) { group.terms = value.split(",").map((term) => term.trim()).filter(Boolean); }
</script>

<template>
  <section class="search-terms-editor" aria-labelledby="search-terms-title">
    <h2 id="search-terms-title" class="editor-title">关键词、同义词与 MeSH 辅助</h2>
    <p class="editor-copy">同一概念内使用 OR；不同概念间使用 AND。请在检索前确认或删除词条。</p>
    <label v-for="group in visibleGroups" :key="group.name" class="term-group">
      <span>{{ group.name }} · {{ group.core_term }}</span>
      <input :value="group.terms.join(', ')" @input="updateTerms(group, ($event.target as HTMLInputElement).value)" />
    </label>
    <ul v-if="props.expanded.mesh_candidates.length" class="mesh-list">
      <li v-for="mesh in props.expanded.mesh_candidates" :key="`${mesh.group_name}-${mesh.mesh_id}`">{{ mesh.descriptor }} ({{ mesh.mesh_id }}) · {{ mesh.source }}</li>
    </ul>
    <p v-for="warning in props.expanded.warnings" :key="warning" class="warning">{{ warning }}</p>
    <button :disabled="props.loading || !visibleGroups.length" @click="emit('build', clone(visibleGroups))">生成 PubMed 检索式</button>
    <div v-if="props.result" class="query-result"><code>{{ props.result.boolean_query }}</code><ul><li v-for="item in props.result.explanations" :key="item">{{ item }}</li></ul></div>
  </section>
</template>

<style scoped>
.search-terms-editor { display: grid; gap: .9rem; padding: 1.25rem; background: #fff; border-radius: 16px; }
.editor-title { margin: 0; color: #173f3c; }.editor-copy { margin: 0; color: #53686b; }.term-group { display: grid; gap: .35rem; color: #40585a; font-weight: 700; }.term-group input { padding: .65rem; border: 1px solid #aabbbb; border-radius: 8px; font: inherit; }.mesh-list, .query-result ul { margin: 0; }.warning { margin: 0; color: #8b5a00; }.search-terms-editor button { justify-self: start; padding: .7rem 1rem; border: 0; border-radius: 8px; background: #173f3c; color: #fff; font-weight: 700; }.query-result { display: grid; gap: .6rem; padding: 1rem; background: #f3f7f5; }.query-result code { overflow-wrap: anywhere; white-space: pre-wrap; }
</style>
