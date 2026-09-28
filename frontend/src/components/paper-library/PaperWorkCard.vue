<script setup lang="ts">
import { computed } from "vue";

import type { PaperItem } from "../../api/paperLibrary";
import { activityLabel, citationLine, entryLabel, readingLabel, relativeDate, roleLabel } from "./paperLibraryFormatters";

const props = defineProps<{ paper: PaperItem; selected: boolean }>();
const emit = defineEmits<{ select: [id: number]; read: [paper: PaperItem]; more: [paper: PaperItem] }>();

const readingEntry = computed(() => props.paper.reading_entry);
const readingProgress = computed(() => props.paper.reading_status === "reading"
  ? `${props.paper.current_section ?? "进行中"} · ${props.paper.reading_progress_percent}%`
  : readingLabel(props.paper.reading_status));
</script>

<template>
  <article
    class="paper-row"
    :class="{ selected }"
    :aria-current="selected ? 'true' : undefined"
    @click="emit('select', paper.id)"
  >
    <div class="file-badge" :class="paper.document_id ? 'pdf' : 'metadata'" aria-hidden="true">
      {{ paper.document_id ? "PDF" : "REF" }}
    </div>
    <div class="paper-copy">
      <a class="paper-title" href="#" @click.prevent.stop="emit('read', paper)">{{ paper.title ?? "未命名论文" }}</a>
      <p class="citation">{{ citationLine(paper) }}</p>
      <div class="property-row">
        <span v-if="paper.paper_type" class="property type">{{ paper.paper_type }}</span>
        <span v-if="paper.journal_quartile" class="property quartile" :title="[paper.journal_quartile_source, paper.journal_quartile_year].filter(Boolean).join(' · ')">{{ paper.journal_quartile }}</span>
        <span v-if="paper.metadata_status === 'pending' || paper.metadata_status === 'running'" class="metadata-state">元数据处理中</span>
        <span v-else-if="paper.metadata_status === 'failed' || paper.metadata_status === 'not_found'" class="metadata-state warning">元数据待补充</span>
      </div>
      <div class="progress-row">
        <span class="reading-dot" aria-hidden="true"></span><span>{{ readingLabel(paper.reading_status) }}</span><b>{{ readingProgress }}</b>
      </div>
      <p class="relation-line">
        <span aria-hidden="true">♙</span>
        <span>{{ paper.primary_relation?.research_name ?? "未关联研究" }}</span>
        <b>{{ roleLabel(paper.primary_relation?.role) }}</b>
        <span v-if="paper.additional_relation_count" class="relation-count">+{{ paper.additional_relation_count }}</span>
      </p>
      <p v-if="paper.recent_activity" class="activity-line">
        <span aria-hidden="true">◷</span>{{ relativeDate(paper.recent_activity.created_at) }} · {{ activityLabel(paper.recent_activity) }}
      </p>
      <p v-else class="activity-line"><span aria-hidden="true">◷</span>暂无最近工作</p>
    </div>
    <div class="work-actions">
      <button
        class="primary-action"
        type="button"
        :disabled="!readingEntry.enabled"
        :title="readingEntry.reason ?? undefined"
        @click.stop="emit('read', paper)"
      >{{ entryLabel("reading", readingEntry) }}</button>
      <div class="secondary-line">
        <button class="more-action" type="button" :aria-label="`${paper.title ?? '论文'}更多操作`" @click.stop="emit('more', paper)">•••</button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.paper-row { position:relative; display:grid; grid-template-columns:48px minmax(0,1fr) 102px; gap:14px; min-height:145px; padding:17px 16px 14px; border-bottom:1px solid var(--line); background:#fff; cursor:pointer; }
.paper-row:hover { background:#fbfdff; }.paper-row.selected { background:#f3f7ff; }.paper-row.selected::before { position:absolute; inset:0 auto 0 0; width:2px; background:var(--blue-600); content:""; }
.file-badge { display:grid; width:38px; height:42px; place-items:center; margin-top:2px; border:1px solid #fecaca; border-radius:4px; background:#fff7f7; color:#ef3340; font-size:10px; font-weight:800; letter-spacing:.02em; }
.file-badge.metadata { border-color:#bbf7d0; background:#f0fdf4; color:#087a55; }.paper-copy { min-width:0; }.paper-title { display:block; overflow:hidden; color:var(--ink-900); font-size:14px; font-weight:750; line-height:1.42; text-decoration:none; text-overflow:ellipsis; white-space:nowrap; }.paper-title:hover { color:var(--blue-600); text-decoration:underline; }
.citation,.relation-line,.activity-line { overflow:hidden; margin:4px 0 0; color:#52627a; font-size:11.5px; line-height:1.35; text-overflow:ellipsis; white-space:nowrap; }.property-row,.progress-row { display:flex; align-items:center; gap:7px; min-height:19px; margin-top:5px; }.property { border-radius:3px; padding:1px 5px; font-size:10.5px; font-weight:700; line-height:17px; }.type { background:#eaf2ff; color:#0b5fcc; }.quartile { background:#f1edff; color:#6d28d9; }.metadata-state { color:#64748b; font-size:10.5px; }.metadata-state.warning { color:#b54708; }
.progress-row { color:#52627a; font-size:11.5px; }.progress-row b { margin-right:9px; color:#334155; font-weight:600; }.reading-dot { width:7px; height:7px; border-radius:50%; background:#18a568; }.relation-line { display:flex; align-items:center; gap:7px; }.relation-line b { color:#334155; font-weight:650; }.relation-count { border-radius:3px; padding:0 5px; background:#eef2f7; color:#64748b; }.activity-line { color:#64748b; }.activity-line span { margin-right:7px; }
.work-actions { display:grid; align-content:start; gap:8px; padding-top:1px; }.work-actions button { min-height:34px; border-radius:4px; padding:0 8px; font:inherit; font-size:12px; font-weight:700; }.primary-action { border:1px solid var(--blue-600); background:var(--blue-600); color:#fff; }.secondary-line { display:flex; justify-content:flex-end; }.more-action { width:30px; border:1px solid var(--line); background:#fff; color:#3b4d66; padding:0 !important; letter-spacing:1px; }.work-actions button:disabled { cursor:not-allowed; opacity:.45; }
@media(max-width:767px){.paper-row{grid-template-columns:38px minmax(0,1fr);min-height:auto;padding:15px 14px;}.file-badge{width:34px;height:38px}.work-actions{grid-column:2;display:flex;flex-wrap:wrap}.work-actions>.primary-action{min-width:112px}.secondary-line{display:flex}.secondary-action{min-width:104px}.more-action{width:40px;min-height:40px}.paper-title{white-space:normal}.progress-row{flex-wrap:wrap}}
</style>
