<script setup lang="ts">
import { computed } from "vue";
import type { RankedCitationItem } from "../../api/literatureSearch";
import SaveToLibraryButton from "../SaveToLibrary/SaveToLibraryButton.vue";
import AbstractDisclosure from "../literature/AbstractDisclosure.vue";
import FulltextAccess from "../literature/FulltextAccess.vue";
import PubMedLink from "../literature/PubMedLink.vue";

interface Props { resultId?: number; items: readonly RankedCitationItem[]; loading: boolean; updating: Readonly<Record<string, boolean>>; currentPage: number; totalPages: number; filteredTotal: number; hasPrevious: boolean; hasNext: boolean; }
const props = defineProps<Props>();
const emit = defineEmits<{ previousPage: []; nextPage: []; goToPage: [page: number]; toggleSaved: [pmid: string, saved: boolean]; toggleRead: [pmid: string, read: boolean]; savedToLibrary: [item: import("../../api/literatureSearch").LibraryItem]; }>();
const pages = computed(() => {
  const start = Math.max(1, props.currentPage - 2);
  const end = Math.min(props.totalPages, props.currentPage + 2);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
});
function authors(authorsValue: readonly string[]): string { const visible = authorsValue.slice(0, 3).join(", "); return authorsValue.length > 3 ? `${visible} 等 ${authorsValue.length} 位` : (visible || "作者未提供"); }
function metadata(entry: RankedCitationItem): string[] { const values = [authors(entry.item.authors), entry.item.journal, entry.item.year === null ? null : String(entry.item.year), entry.item.pmid ? `PMID ${entry.item.pmid}` : null, entry.item.doi ? `DOI ${entry.item.doi}` : null]; return values.filter((value): value is string => Boolean(value)); }
</script>

<template>
  <section class="results" aria-labelledby="results-title">
    <header class="results-header">
      <h2 id="results-title">结果概览</h2>
      <p v-if="props.loading" class="count-note">正在读取结果</p>
      <p v-else-if="props.filteredTotal" class="count-note">筛选后共 {{ props.filteredTotal }} 条</p>
      <p v-else class="count-note">暂无可展示结果</p>
    </header>

    <div v-if="props.loading" class="loading-list" aria-live="polite">
      <div v-for="row in 3" :key="row" class="loading-row"><span /><span /><span /></div>
      <p>正在读取检索结果…</p>
    </div>
    <p v-else-if="items.length === 0" class="empty-state">当前筛选条件下没有结果。请调整筛选条件，或返回检索中心执行新的真实检索。</p>
    <ol v-else class="result-list">
      <li v-for="(entry, index) in items" :key="entry.item.pmid" class="result-row">
        <span class="result-index" :aria-label="`当前页第 ${index + 1} 条`">{{ index + 1 }}</span>
        <article class="record-body">
          <h3 class="record-title">{{ entry.item.title ?? "标题未提供" }}</h3>
          <p class="record-meta">{{ metadata(entry).join(" · ") }}</p>
          <div class="record-evidence">
            <span v-if="entry.item.verified" class="verified" :title="entry.item.verified_by ?? ''">PubMed 已核实</span>
            <span v-if="entry.sort_reason" class="sort-reason" :title="entry.sort_reason">排序理由：{{ entry.sort_reason }}</span>
            <span v-if="entry.state?.tags?.length" class="tags">标签：{{ entry.state.tags.join(" · ") }}</span>
          </div>
          <AbstractDisclosure :abstract-text="entry.item.abstract" />
        </article>
        <div class="record-actions" aria-label="记录操作">
          <button class="action-button" :class="{ active: entry.state?.saved }" :disabled="props.loading || props.updating[entry.item.pmid]" @click="emit('toggleSaved', entry.item.pmid, !entry.state?.saved)">{{ entry.state?.saved ? "已保存" : "保存" }}</button>
          <SaveToLibraryButton v-if="resultId !== undefined" :result-id="resultId" :pmid="entry.item.pmid" :disabled="props.loading || props.updating[entry.item.pmid]" @saved="emit('savedToLibrary', $event)" />
          <button class="action-button" :class="{ active: entry.state?.read_status === 'read' }" :disabled="props.loading || props.updating[entry.item.pmid]" @click="emit('toggleRead', entry.item.pmid, entry.state?.read_status !== 'read')">{{ entry.state?.read_status === "read" ? "已读" : "标记已读" }}</button>
          <PubMedLink :pmid="entry.item.pmid" />
          <FulltextAccess :item="entry.library_item" />
        </div>
      </li>
    </ol>

    <nav v-if="filteredTotal > 0 && totalPages > 1" class="pagination" aria-label="结果分页">
      <button :disabled="props.loading || !props.hasPrevious" @click="emit('previousPage')">上一页</button>
      <button v-for="page in pages" :key="page" :class="{ current: page === props.currentPage }" :disabled="props.loading || page === props.currentPage" @click="emit('goToPage', page)">{{ page }}</button>
      <button :disabled="props.loading || !props.hasNext" @click="emit('nextPage')">下一页</button>
    </nav>
  </section>
</template>

<style scoped>
.results { display: grid; gap: 0; overflow: hidden; border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 8px; background: var(--surface, #fff); box-shadow: var(--shadow-card, 0 2px 8px rgb(15 42 67 / 4%)); }
.results-header { display: flex; align-items: center; gap: .75rem; min-height: 3.25rem; padding: 0 .95rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); }
.results-header h2 { margin: 0; color: var(--text-primary, #0f2a43); font-size: .95rem; }
.count-note { margin: 0; color: var(--text-muted, #64748b); font-size: .8rem; }
.result-list { margin: 0; padding: 0; list-style: none; }
.result-row { display: grid; grid-template-columns: 2rem minmax(0, 1fr) minmax(17rem, auto); gap: .75rem; align-items: start; padding: .82rem .95rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); }
.result-index { display: grid; place-items: center; min-width: 1.5rem; min-height: 1.5rem; color: var(--text-muted, #64748b); font-size: .82rem; font-weight: 700; }
.record-body { display: grid; min-width: 0; gap: .35rem; }
.record-title { margin: 0; color: var(--color-primary, #2563eb); font-size: .93rem; line-height: 1.45; overflow-wrap: anywhere; }
.record-meta { margin: 0; color: var(--text-muted, #64748b); font-size: .78rem; line-height: 1.45; overflow-wrap: anywhere; }
.record-evidence { display: flex; gap: .5rem; flex-wrap: wrap; color: var(--text-faint, #94a3b8); font-size: .74rem; }
.verified { color: var(--color-success, #15803d); font-weight: 600; }
.sort-reason, .tags { overflow-wrap: anywhere; }
.record-body :deep(.abstract-disclosure) { margin-top: .15rem; }
.record-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: .38rem .55rem; max-width: 26rem; padding-top: .02rem; font-size: .78rem; }
.action-button, .record-actions :deep(button), .record-actions :deep(a), .record-actions :deep(.fulltext-access) { min-height: 1.85rem; box-sizing: border-box; white-space: nowrap; }
.action-button { padding: .28rem .52rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; color: var(--text-primary, #0f2a43); font: inherit; cursor: pointer; }
.action-button.active { border-color: color-mix(in srgb, var(--color-primary, #2563eb) 45%, white); background: var(--color-primary-soft, #eff6ff); color: var(--color-primary, #2563eb); }
.action-button:focus-visible, .pagination button:focus-visible { outline: 2px solid var(--color-primary, #2563eb); outline-offset: 2px; }
.loading-list { display: grid; gap: .65rem; padding: 1rem; color: var(--text-muted, #64748b); font-size: .82rem; }
.loading-list p { margin: 0; }.loading-row { display: grid; grid-template-columns: 2rem 1fr 14rem; gap: .75rem; }.loading-row span { height: 1.25rem; border-radius: 4px; background: var(--surface-muted, #f1f5f9); }
.empty-state { margin: 0; padding: 2.4rem 1rem; color: var(--text-muted, #64748b); font-size: .88rem; text-align: center; }
.pagination { display: flex; justify-content: center; gap: .4rem; padding: .75rem; }.pagination button { min-width: 2rem; padding: .34rem .6rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; color: var(--text-primary, #0f2a43); font: inherit; font-size: .8rem; cursor: pointer; }.pagination button.current { border-color: var(--color-primary, #2563eb); background: var(--color-primary, #2563eb); color: #fff; }.pagination button:disabled { opacity: .55; cursor: not-allowed; }
@media (max-width: 900px) { .result-row { grid-template-columns: 1.6rem minmax(0, 1fr); }.record-actions { grid-column: 2; justify-content: flex-start; max-width: none; }.loading-row { grid-template-columns: 1.5rem 1fr; }.loading-row span:last-child { display: none; } }
@media (prefers-reduced-motion: no-preference) { .result-row, .action-button { transition: background-color 150ms ease, border-color 150ms ease; } .result-row:hover { background: var(--surface-muted, #f8fafc); } }
</style>
