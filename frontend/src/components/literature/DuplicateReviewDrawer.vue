<script setup lang="ts">
import { computed, shallowRef } from "vue";

import type { DeduplicationSummary, DuplicateGroup, ResultDuplicateResolutionAction } from "../../api/literatureSearch";

type GroupStatus = "pending_resolution" | "all";

const props = defineProps<{
  open: boolean;
  summary: DeduplicationSummary | null;
  groups: DuplicateGroup[];
  status: GroupStatus;
  page: number;
  totalPages: number;
  loading: boolean;
  error: string;
}>();
const emit = defineEmits<{
  close: [];
  scan: [];
  loadGroups: [status: GroupStatus, page: number];
  resolve: [groupId: number, action: ResultDuplicateResolutionAction, recordKey?: string];
}>();

const selectedKeys = shallowRef<Record<number, string>>({});
const visibleGroups = computed(() => props.groups);

function choose(groupId: number, value: string): void {
  selectedKeys.value = { ...selectedKeys.value, [groupId]: value };
}

function selectGroupStatus(status: GroupStatus): void {
  emit("loadGroups", status, 1);
}
</script>

<template>
  <section
    v-if="props.open"
    class="drawer-backdrop"
    @click.self="emit('close')"
  >
    <aside
      class="drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      tabindex="-1"
      @keydown.esc="emit('close')"
    >
      <header class="drawer-header">
        <div>
          <p class="kicker">重复论文工作区</p>
          <h2 id="drawer-title">检查与确认重复论文</h2>
        </div>
        <button
          type="button"
          aria-label="关闭重复论文工作区"
          @click="emit('close')"
        >
          关闭
        </button>
      </header>

      <p
        v-if="props.error"
        class="error"
        role="alert"
      >
        {{ props.error }}
      </p>

      <template v-if="props.summary?.has_scan">
        <section
          class="summary"
          aria-label="重复论文摘要"
        >
          <span>已检查 {{ props.summary.scanned_count }} 篇</span>
          <span>明确重复 {{ props.summary.clear_group_count }} 组</span>
          <span>待确认 {{ props.summary.pending_group_count }} 组</span>
          <span>合并视图当前 {{ props.summary.consolidated_visible_count }} 篇</span>
        </section>

        <nav
          class="group-tabs"
          aria-label="重复论文分组筛选"
        >
          <button
            type="button"
            :class="{ active: props.status === 'pending_resolution' }"
            @click="selectGroupStatus('pending_resolution')"
          >
            待人工确认
          </button>
          <button
            type="button"
            :class="{ active: props.status === 'all' }"
            @click="selectGroupStatus('all')"
          >
            查看系统归并记录
          </button>
        </nav>

        <p
          v-if="visibleGroups.length === 0 && !props.loading"
          class="empty"
        >
          {{ props.status === 'pending_resolution' ? '没有待人工确认的重复组。' : '当前没有可查看的系统归并记录。' }}
        </p>

        <article
          v-for="group in visibleGroups"
          :key="group.id"
          class="group"
        >
          <header class="group-header">
            <p class="match">{{ group.confidence === 'fuzzy' ? '需要人工确认' : '系统归并记录' }}</p>
            <p class="explanation">匹配依据：{{ group.match_explanation }}</p>
          </header>
          <div
            v-for="member in group.members"
            :key="member.record_key ?? member.record_pmid"
            class="member"
            :class="{ canonical: member.is_canonical }"
          >
            <label>
              <input
                type="radio"
                :name="`group-${group.id}`"
                :value="member.record_key ?? ''"
                :checked="selectedKeys[group.id] === member.record_key"
                :disabled="!member.record_key || group.confidence !== 'fuzzy'"
                @change="choose(group.id, member.record_key ?? '')"
              >
              <strong>{{ member.title || '题名未提供' }}</strong>
              <span
                v-if="member.is_canonical"
                class="canonical-label"
              >系统推荐保留项</span>
            </label>
            <p>{{ member.authors.join('、') || '作者未提供' }} · {{ member.journal || '期刊未提供' }} · {{ member.year ?? '年份未提供' }}</p>
            <p>PMID {{ member.pmid || member.record_pmid }}<span v-if="member.doi"> · DOI {{ member.doi }}</span><span v-if="member.verified"> · PubMed 已核实</span></p>
          </div>
          <footer
            v-if="group.confidence === 'fuzzy'"
            class="group-actions"
          >
            <button
              type="button"
              :disabled="!selectedKeys[group.id] || props.loading"
              @click="emit('resolve', group.id, 'merge', selectedKeys[group.id])"
            >
              确认为同一篇并保留所选项
            </button>
            <button
              type="button"
              :disabled="props.loading"
              @click="emit('resolve', group.id, 'keep_all')"
            >
              分别保留
            </button>
            <button
              type="button"
              :disabled="props.loading"
              @click="emit('resolve', group.id, 'undo')"
            >
              撤销判断
            </button>
          </footer>
        </article>

        <nav
          v-if="props.totalPages > 1"
          class="group-pagination"
          aria-label="重复论文分组分页"
        >
          <button
            type="button"
            :disabled="props.loading || props.page === 1"
            @click="emit('loadGroups', props.status, props.page - 1)"
          >
            上一页
          </button>
          <span>第 {{ props.page }} 页，共 {{ props.totalPages }} 页</span>
          <button
            type="button"
            :disabled="props.loading || props.page === props.totalPages"
            @click="emit('loadGroups', props.status, props.page + 1)"
          >
            下一页
          </button>
        </nav>
      </template>

      <section
        v-else
        class="scan-empty"
      >
        <p>尚未检查这批检索结果中的重复论文。检查不会删除原始记录，之后可随时调整判断。</p>
        <button
          type="button"
          :disabled="props.loading"
          @click="emit('scan')"
        >
          {{ props.loading ? '正在检查…' : '检查重复论文' }}
        </button>
      </section>
    </aside>
  </section>
</template>

<style scoped>
.drawer-backdrop { position: fixed; inset: 0; z-index: 30; background: rgb(15 23 42 / 33%); }
.drawer { position: absolute; inset: 0 0 0 auto; width: min(48rem, 100%); overflow-y: auto; overscroll-behavior: contain; background: var(--surface); padding: 1.25rem; box-shadow: -16px 0 36px rgb(15 23 42 / 14%); }
.drawer-header { display: flex; justify-content: space-between; gap: 1rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: .9rem; }.drawer-header h2 { margin: .2rem 0; font-size: 1.2rem; }
.kicker, .match, .explanation { margin: 0; color: var(--text-muted); font-size: .75rem; }.explanation { margin-top: .25rem; line-height: 1.45; }
.summary { display: flex; flex-wrap: wrap; gap: .5rem; padding: 1rem 0; }.summary span { padding: .25rem .45rem; background: var(--surface-muted); color: var(--text-primary); font-size: .78rem; font-variant-numeric: tabular-nums; }
.group-tabs { display: flex; gap: .4rem; border-bottom: 1px solid var(--border-subtle); }.group-tabs button { border: 0; border-bottom: 3px solid transparent; padding: .5rem 0; background: transparent; color: var(--text-muted); font: inherit; font-size: .82rem; cursor: pointer; }.group-tabs button + button { margin-left: 1rem; }.group-tabs button.active { border-color: var(--color-primary); color: var(--text-primary); font-weight: 700; }
.group { border-bottom: 1px solid var(--border-subtle); padding: 1rem 0; }.group-header { margin-bottom: .55rem; }.member { padding: .7rem; border: 1px solid var(--border-subtle); border-bottom: 0; }.member:last-of-type { border-bottom: 1px solid var(--border-subtle); }.member.canonical { border-left: 3px solid var(--color-primary); }.member label { display: flex; align-items: start; gap: .45rem; }.member p { margin: .3rem 0 0 1.4rem; color: var(--text-muted); font-size: .8rem; line-height: 1.45; }.canonical-label { margin-left: auto; color: var(--color-primary); font-size: .72rem; font-weight: 700; white-space: nowrap; }
.group-actions, .group-pagination { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; padding-top: .75rem; }.group-actions button, .drawer-header button, .scan-empty button, .group-pagination button { padding: .45rem .65rem; border: 1px solid var(--border-strong); background: var(--surface); color: var(--text-primary); font: inherit; cursor: pointer; }.group-actions button:first-child, .scan-empty button { border-color: var(--color-primary); background: var(--color-primary); color: #fff; }.group-actions button:disabled, .scan-empty button:disabled, .group-pagination button:disabled { opacity: .55; cursor: not-allowed; }.group-pagination { justify-content: space-between; }.group-pagination span { color: var(--text-muted); font-size: .8rem; font-variant-numeric: tabular-nums; }
.error { margin: .8rem 0 0; color: var(--color-danger); }.empty, .scan-empty { color: var(--text-muted); line-height: 1.55; }.scan-empty { padding: 1.25rem 0; }.drawer button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
</style>
