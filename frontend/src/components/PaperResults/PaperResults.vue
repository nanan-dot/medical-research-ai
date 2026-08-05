<script setup lang="ts">
import type { RankedCitationItem } from "../../api/literatureSearch";
import SaveToLibraryButton from "../SaveToLibrary/SaveToLibraryButton.vue";

interface Props {
  resultId?: number;
  items: readonly RankedCitationItem[];
  loading: boolean;
  updating: Readonly<Record<string, boolean>>;
  currentPage: number;
  totalPages: number;
  filteredTotal: number;
  hasPrevious: boolean;
  hasNext: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  previousPage: [];
  nextPage: [];
  goToPage: [page: number];
  toggleSaved: [pmid: string, saved: boolean];
  toggleRead: [pmid: string, read: boolean];
  savedToLibrary: [reason: string];
}>();

const PAGE_RANGE = 2;

function pagesToShow(current: number, total: number): number[] {
  const start = Math.max(1, current - PAGE_RANGE);
  const end = Math.min(total, current + PAGE_RANGE);
  const pages: number[] = [];
  for (let index = start; index <= end; index += 1) pages.push(index);
  return pages;
}

function formatAuthors(authors: readonly string[]): string {
  if (authors.length === 0) return "作者未提供";
  const joined = authors.slice(0, 3).join(", ");
  return authors.length > 3 ? `${joined} 等 ${authors.length} 位` : joined;
}

function journalYear(item: RankedCitationItem["item"]): string {
  if (item.journal && item.year !== null) return `${item.journal} · ${item.year}`;
  if (item.journal) return item.journal;
  if (item.year !== null) return `${item.year}`;
  return "年份未提供";
}

function abstractState(item: RankedCitationItem["item"]): string {
  return item.has_abstract ? "有摘要" : "无摘要";
}
</script>

<template>
  <section class="results" aria-labelledby="results-title">
    <header class="results-header">
      <h2 id="results-title">检索结果</h2>
      <p class="count-note">筛选后共 {{ filteredTotal }} 条</p>
    </header>

    <p v-if="loading" class="state-text">正在读取检索结果…</p>
    <p v-else-if="items.length === 0" class="empty-state">当前筛选条件下没有结果，请调整筛选条件。</p>
    <ul v-else class="result-list">
      <li v-for="entry in items" :key="entry.item.pmid" class="result-item">
        <div class="item-head">
          <h3 class="item-title">{{ entry.item.title ?? "标题未提供" }}</h3>
          <div class="user-state">
            <button
              class="state-chip"
              :class="{ active: entry.state?.saved }"
              :disabled="loading || updating[entry.item.pmid]"
              @click="emit('toggleSaved', entry.item.pmid, !entry.state?.saved)"
            >
              {{ entry.state?.saved ? "★ 已保存" : "☆ 保存" }}
            </button>
            <SaveToLibraryButton v-if="resultId !== undefined" :result-id="resultId" :pmid="entry.item.pmid" :disabled="loading || updating[entry.item.pmid]" @saved="emit('savedToLibrary', $event.fulltext_status_reason)" />
            <button
              class="state-chip"
              :class="{ active: entry.state?.read_status === 'read' }"
              :disabled="loading || updating[entry.item.pmid]"
              @click="emit('toggleRead', entry.item.pmid, entry.state?.read_status !== 'read')"
            >
              {{ entry.state?.read_status === "read" ? "已读" : "标记已读" }}
            </button>
          </div>
        </div>
        <p class="item-meta">{{ formatAuthors(entry.item.authors) }} · {{ journalYear(entry.item) }}</p>
        <p class="item-meta">{{ abstractState(entry.item) }}<template v-if="entry.item.publication_types.length"> · {{ entry.item.publication_types.join(", ") }}</template></p>
        <div class="item-foot">
          <span class="pmid">PMID {{ entry.item.pmid }}</span>
          <span v-if="entry.item.verified" class="verified" :title="entry.item.verified_by ?? ''">PubMed 已核实</span>
          <span class="sort-reason" :title="entry.sort_reason">排序理由：{{ entry.sort_reason }}</span>
        </div>
        <div v-if="entry.state?.tags?.length" class="tags">标签：{{ entry.state.tags.join(" · ") }}</div>
      </li>
    </ul>

    <nav v-if="filteredTotal > 0 && totalPages > 1" class="pagination" aria-label="结果分页">
      <button :disabled="loading || !hasPrevious" @click="emit('previousPage')">上一页</button>
      <template v-for="page in pagesToShow(currentPage, totalPages)" :key="page">
        <button
          class="page-number"
          :class="{ current: page === currentPage }"
          :disabled="loading || page === currentPage"
          @click="emit('goToPage', page)"
        >
          {{ page }}
        </button>
      </template>
      <button :disabled="loading || !hasNext" @click="emit('nextPage')">下一页</button>
      <span class="page-note">第 {{ currentPage }} / {{ totalPages }} 页</span>
    </nav>
  </section>
</template>

<style scoped>
.results { display: grid; gap: 0.9rem; }
.results-header { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
.results-header h2 { margin: 0; color: var(--text-primary); font-size: 1.35rem; }
.count-note { margin: 0; color: var(--text-muted); font-size: 0.86rem; }
.state-text { padding: 1.2rem; color: var(--text-muted); }
.empty-state { padding: 2rem; border: 1px dashed var(--border-strong); border-radius: var(--radius-md); text-align: center; color: var(--text-muted); }
.result-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.7rem; }
.result-item { display: grid; gap: 0.5rem; padding: 0.9rem 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface); box-shadow: var(--shadow-card); }
.item-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.8rem; }
.item-title { margin: 0; color: var(--text-primary); font-size: 1.02rem; line-height: 1.45; overflow-wrap: anywhere; flex: 1; min-width: 0; }
.user-state { display: flex; gap: 0.4rem; flex-shrink: 0; }
.state-chip { border: 1px solid var(--border-strong); border-radius: 99px; padding: 0.3rem 0.6rem; background: var(--paper); color: var(--text-muted); font-size: 0.76rem; font-weight: 750; white-space: nowrap; }
.state-chip.active { border-color: transparent; background: var(--color-primary-soft); color: var(--color-primary); }
.state-chip:disabled { opacity: 0.55; }
.item-meta { margin: 0; color: var(--text-muted); font-size: 0.84rem; }
.item-foot { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; border-top: 1px solid var(--border-subtle); padding-top: 0.5rem; font-size: 0.76rem; }
.pmid { color: var(--text-faint); font-family: ui-monospace, "SF Mono", Consolas, monospace; }
.verified { color: var(--color-success); font-weight: 750; }
.sort-reason { color: var(--text-faint); overflow-wrap: anywhere; }
.tags { color: var(--color-primary); font-size: 0.8rem; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 0.4rem; flex-wrap: wrap; }
.pagination button { border: 1px solid var(--border-strong); border-radius: 8px; padding: 0.45rem 0.75rem; background: var(--surface); color: var(--text-primary); font-weight: 700; }
.pagination button:disabled { opacity: 0.5; }
.pagination .page-number.current { border-color: transparent; background: var(--color-primary); color: #fff; }
.page-note { color: var(--text-muted); font-size: 0.84rem; margin-left: 0.4rem; }
</style>
