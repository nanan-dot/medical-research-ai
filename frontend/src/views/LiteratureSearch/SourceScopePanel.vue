<script setup lang="ts">
// 来源范围：本地表单状态选择检索数据库候选。
// 明确边界：此处是用户选择的前端状态，不声称已经访问这些数据库；
// 执行检索时使用后端 createTask 的 database 字段（当前为 pubmed 单库）。
import { computed, onMounted } from "vue";

const emit = defineEmits<{
  change: [selected: string[]];
  languageChange: [value: "any" | "chinese"];
}>();
const props = defineProps<{ publicationLanguage: "any" | "chinese" }>();
const languageModel = computed({
  get: () => props.publicationLanguage,
  set: (value: "any" | "chinese") => emit("languageChange", value),
});
// 当前服务端 createTask 仅支持 PubMed。未接入来源保持不可选，避免让用户误以为会参与检索。
onMounted(() => emit("change", ["pubmed"]));
</script>

<template>
  <section class="source-panel" aria-labelledby="source-panel-title">
    <h3 id="source-panel-title" class="panel-title">3. 来源范围</h3>
    <div class="source-list" role="group" aria-label="检索数据库来源">
      <label class="source-option">
        <input :checked="true" type="checkbox" aria-label="PubMed，已纳入检索" @click.prevent />
        <span>PubMed</span>
      </label>
      <label class="source-option unavailable">
        <input type="checkbox" disabled aria-label="Embase，尚未接入" />
        <span>Embase <small>未接入</small></span>
      </label>
      <label class="source-option unavailable">
        <input type="checkbox" disabled aria-label="Cochrane Library，尚未接入" />
        <span>Cochrane Library <small>未接入</small></span>
      </label>
    </div>
    <p class="source-note">本次检索仅提交至 PubMed。</p>
    <label class="language-filter">
      <span>文献发表语言</span>
      <select v-model="languageModel" aria-label="文献发表语言">
        <option value="any">不限发表语言（推荐）</option>
        <option value="chinese">仅中文发表文献</option>
      </select>
    </label>
    <p class="language-note">
      {{ languageModel === "chinese" ? "将附加 chinese[la]，可能排除其他语言发表的证据。" : "中文输入会自动转换检索术语，不会限制文献发表语言。" }}
    </p>
  </section>
</template>

<style scoped>
.source-panel {
  display: grid;
  gap: .55rem;
  padding: .85rem 1rem;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 0;
  align-content: start;
}
.panel-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: 1rem;
}
.source-list {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}
.source-option {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: .82rem;
  color: var(--text-primary, #0f2a43);
  cursor: pointer;
}
.source-option input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--color-primary, #2563eb);
}
.source-option input:focus-visible {
  outline: 2px solid var(--color-primary, #2563eb);
  outline-offset: 2px;
}
.source-option.unavailable { color: var(--text-muted, #64748b); cursor: not-allowed; }
.source-option small { margin-left: .35rem; font-size: .75rem; }
.source-note {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted, #64748b);
}
.language-filter { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px; align-items: center; max-width: 420px; color: var(--text-secondary, #475569); font-size: .78rem; font-weight: 600; }
.language-filter select { min-height: 2rem; padding: 0 .5rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: var(--surface, #fff); color: var(--text-primary, #0f2a43); font: inherit; font-size: .78rem; }
.language-note { margin: -.2rem 0 0; color: var(--text-muted, #64748b); font-size: .72rem; line-height: 1.4; }
@media (max-width: 560px) { .source-list { display: grid; gap: .45rem; } }
</style>
