<script setup lang="ts">
import { computed } from "vue";
import type { RankedCitationItem } from "../../api/literatureSearch";
import { DEFAULT_PAGE_SIZE } from "../../composables/useLiteratureResults";
import SaveToLibraryButton from "../SaveToLibrary/SaveToLibraryButton.vue";
import AbstractDisclosure from "../literature/AbstractDisclosure.vue";
import FulltextAccess from "../literature/FulltextAccess.vue";
import PubMedLink from "../literature/PubMedLink.vue";

interface Props { resultId?: number; items: readonly RankedCitationItem[]; loading: boolean; updating: Readonly<Record<string, boolean>>; currentPage: number; pageSize?: number; totalPages: number; filteredTotal: number; hasPrevious: boolean; hasNext: boolean; }
const props = withDefaults(defineProps<Props>(), { pageSize: DEFAULT_PAGE_SIZE });
const emit = defineEmits<{ previousPage: []; nextPage: []; goToPage: [page: number]; toggleSaved: [pmid: string, saved: boolean]; toggleRead: [pmid: string, read: boolean]; savedToLibrary: [item: import("../../api/literatureSearch").LibraryItem]; }>();
const pages = computed(() => {
  const start = Math.max(1, props.currentPage - 2);
  const end = Math.min(props.totalPages, props.currentPage + 2);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
});
const visibleRange = computed(() => {
  if (props.filteredTotal === 0) return null;
  const first = (props.currentPage - 1) * props.pageSize + 1;
  return { first, last: Math.min(props.currentPage * props.pageSize, props.filteredTotal) };
});
function authors(authorsValue: readonly string[]): string { const visible = authorsValue.slice(0, 3).join(", "); return authorsValue.length > 3 ? `${visible} 等 ${authorsValue.length} 位` : (visible || "作者未提供"); }
function metadata(entry: RankedCitationItem): string[] { const values = [authors(entry.item.authors), entry.item.journal, entry.item.year === null ? null : String(entry.item.year), entry.item.pmid ? `PMID ${entry.item.pmid}` : null, entry.item.doi ? `DOI ${entry.item.doi}` : null]; return values.filter((value): value is string => Boolean(value)); }
function readingSignals(entry: RankedCitationItem): string[] {
  const signals = entry.item.publication_types.slice(0, 2);
  if (entry.item.verified) signals.push("PubMed 已核实");
  return signals;
}
</script>

<template>
  <section class="results" aria-label="检索结果">
    <div v-if="visibleRange" class="results-navigation" role="status" aria-live="polite">
      <p class="range-note">共 {{ props.filteredTotal }} 条 · 当前显示第 {{ visibleRange.first }}–{{ visibleRange.last }} 条</p>
      <div v-if="props.totalPages > 1" class="navigation-controls" aria-label="顶部结果分页">
        <button :disabled="props.loading || !props.hasPrevious" aria-label="上一页" @click="emit('previousPage')">上一页</button>
        <span>第 {{ props.currentPage }} 页，共 {{ props.totalPages }} 页</span>
        <button :disabled="props.loading || !props.hasNext" aria-label="下一页" @click="emit('nextPage')">下一页</button>
      </div>
    </div>
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
          <div class="reading-signals" aria-label="文献阅读信号">
            <span v-for="signal in readingSignals(entry)" :key="signal" class="signal-chip">{{ signal }}</span>
            <span v-if="entry.state?.tags?.length" class="tags">标签：{{ entry.state.tags.join(" · ") }}</span>
          </div>
          <AbstractDisclosure :abstract-text="entry.item.abstract" />
        </article>
        <div class="record-actions record-actions--rail record-actions--horizontal" aria-label="记录操作">
          <button class="action-button" :class="{ active: entry.state?.saved }" :aria-pressed="entry.state?.saved === true" :disabled="props.loading || Boolean(props.updating[entry.item.pmid])" @click="emit('toggleSaved', entry.item.pmid, !entry.state?.saved)">{{ entry.state?.saved ? "已保存" : "保存" }}</button>
          <SaveToLibraryButton v-if="resultId !== undefined" :result-id="resultId" :pmid="entry.item.pmid" :disabled="props.loading || Boolean(props.updating[entry.item.pmid])" @saved="emit('savedToLibrary', $event)" />
          <button class="action-button" :class="{ active: entry.state?.read_status === 'read' }" :aria-pressed="entry.state?.read_status === 'read'" :disabled="props.loading || Boolean(props.updating[entry.item.pmid])" @click="emit('toggleRead', entry.item.pmid, entry.state?.read_status !== 'read')">{{ entry.state?.read_status === "read" ? "已读" : "标记已读" }}</button>
          <PubMedLink :pmid="entry.item.pmid" />
          <FulltextAccess :item="entry.library_item" />
        </div>
      </li>
    </ol>

    <nav v-if="filteredTotal > 0 && totalPages > 1" class="pagination" aria-label="结果分页">
      <button :disabled="props.loading || !props.hasPrevious" aria-label="上一页" @click="emit('previousPage')">上一页</button>
      <button v-for="page in pages" :key="page" :class="{ current: page === props.currentPage }" :disabled="props.loading || page === props.currentPage" @click="emit('goToPage', page)">{{ page }}</button>
      <button :disabled="props.loading || !props.hasNext" aria-label="下一页" @click="emit('nextPage')">下一页</button>
    </nav>
  </section>
</template>

<style scoped>
.results { display: grid; gap: 0; overflow: hidden; border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 8px; background: var(--surface, #fff); box-shadow: var(--shadow-card, 0 2px 8px rgb(15 42 67 / 4%)); }
.results-navigation { display: flex; align-items: center; justify-content: space-between; gap: .75rem; padding: .48rem .95rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); background: var(--surface-muted, #f8fafc); }
.range-note { margin: 0; color: var(--text-muted, #64748b); font-size: .8rem; }
.navigation-controls { display: flex; align-items: center; gap: .45rem; color: var(--text-muted); font-size: .78rem; white-space: nowrap; }
.navigation-controls button { min-height: 2rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; padding: .28rem .52rem; background: var(--surface, #fff); color: var(--text-primary, #0f2a43); font: inherit; font-size: .78rem; cursor: pointer; }
.navigation-controls button:disabled { opacity: .55; cursor: not-allowed; }
.result-list { margin: 0; padding: 0; list-style: none; }
.result-row { display: grid; grid-template-columns: 2rem minmax(0, 1fr) 17rem; gap: .8rem; align-items: stretch; padding: .9rem .95rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); }
.result-index { display: grid; place-items: start center; padding-top: .2rem; min-width: 1.5rem; color: var(--text-muted, #64748b); font-size: .8rem; font-weight: 800; }
.record-body { display: grid; min-width: 0; gap: .42rem; }
.record-title { margin: 0; color: var(--color-primary, #2563eb); font-size: 1.02rem; line-height: 1.42; overflow-wrap: anywhere; }
.record-meta { margin: 0; color: var(--text-muted, #64748b); font-size: .8rem; line-height: 1.4; overflow-wrap: anywhere; }
.reading-signals { display: flex; gap: .35rem; flex-wrap: wrap; font-size: .72rem; }
.signal-chip, .tags { border-radius: 999px; padding: .18rem .48rem; background: var(--surface-muted, #f1f5f9); color: var(--text-secondary, #475569); overflow-wrap: anywhere; }
.record-body :deep(.abstract-disclosure) { margin-top: .08rem; }.record-body :deep(.abstract-disclosure button) { padding: 0; border: 0; background: transparent; color: var(--color-primary); font-size: .78rem; }
.record-actions--rail { min-width: 0; padding-left: .8rem; border-left: 1px solid var(--border-subtle, #dbe4f0); font-size: .78rem; }
.record-actions--horizontal { display: flex; align-content: start; align-items: center; gap: .42rem; flex-wrap: wrap; }
.action-button, .record-actions :deep(button), .record-actions :deep(a), .record-actions :deep(.fulltext-access) { box-sizing: border-box; min-height: 2rem; }
.action-button { padding: .32rem .55rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; color: var(--text-primary, #0f2a43); font: inherit; cursor: pointer; white-space: nowrap; }
.action-button.active { border-color: color-mix(in srgb, var(--color-primary, #2563eb) 45%, white); background: var(--color-primary-soft, #eff6ff); color: var(--color-primary, #2563eb); }
.record-actions :deep(.save-library), .record-actions :deep(.save-library .button) { width: auto; white-space: nowrap; }.record-actions :deep(a), .record-actions :deep(.fulltext-access) { display: inline-flex; align-items: center; padding-top: 0; line-height: 1.3; white-space: nowrap; }
.action-button:focus-visible, .navigation-controls button:focus-visible, .pagination button:focus-visible { outline: 2px solid var(--color-primary, #2563eb); outline-offset: 2px; }
.loading-list { display: grid; gap: .65rem; padding: 1rem; color: var(--text-muted, #64748b); font-size: .82rem; }
.loading-list p { margin: 0; }.loading-row { display: grid; grid-template-columns: 2rem 1fr 14rem; gap: .75rem; }.loading-row span { height: 1.25rem; border-radius: 4px; background: var(--surface-muted, #f1f5f9); }
.empty-state { margin: 0; padding: 2.4rem 1rem; color: var(--text-muted, #64748b); font-size: .88rem; text-align: center; }
.pagination { display: flex; justify-content: center; align-items: center; gap: .4rem; padding: .55rem; }.pagination-top { justify-content: space-between; padding: .42rem .75rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); background: var(--surface-muted, #f8fafc); }.page-position { color: var(--text-muted); font-size: .78rem; }.pagination button { min-width: 2rem; padding: .28rem .52rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; color: var(--text-primary, #0f2a43); font: inherit; font-size: .78rem; cursor: pointer; }.pagination button.current { border-color: var(--color-primary, #2563eb); background: var(--color-primary, #2563eb); color: #fff; }.pagination button:disabled { opacity: .55; cursor: not-allowed; }
@media (max-width: 1200px) { .result-row { grid-template-columns: 2rem minmax(0, 1fr); }.record-actions--rail { grid-column: 2; padding: .7rem 0 0; border-top: 1px solid var(--border-subtle, #dbe4f0); border-left: 0; }.loading-row { grid-template-columns: 1.5rem 1fr; }.loading-row span:last-child { display: none; } }
@media (max-width: 640px) { .results-navigation { align-items: start; flex-direction: column; }.navigation-controls { width: 100%; justify-content: space-between; }.result-row { gap: .55rem; padding: .72rem; }.result-index { min-width: 1.25rem; }.record-actions--rail { grid-template-columns: repeat(2, minmax(0, 1fr)); }.record-actions :deep(.fulltext-access) { grid-column: auto; }.record-actions :deep(a), .record-actions :deep(.fulltext-access) { padding-top: 0; }.record-meta { font-size: .74rem; } }
@media (prefers-reduced-motion: no-preference) { .result-row, .action-button { transition: background-color 150ms ease, border-color 150ms ease; } .result-row:hover { background: var(--surface-muted, #f8fafc); } }
</style>
