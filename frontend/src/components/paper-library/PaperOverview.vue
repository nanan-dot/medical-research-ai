<script setup lang="ts">
import { computed, shallowRef } from "vue";

import type { PaperOverview } from "../../api/paperLibrary";
import BaseIcon from "../ui/BaseIcon.vue";
import {
  activityLabel,
  citationLine,
  entryLabel,
  relativeDate,
  roleLabel,
} from "./paperLibraryFormatters";

const props = defineProps<{
  open: boolean;
  paper: PaperOverview | null;
  loading: boolean;
  error: string | null;
  actionPending: boolean;
}>();
const emit = defineEmits<{
  close: [];
  retry: [];
  read: [paper: PaperOverview];
  resource: [paper: PaperOverview];
  editRelations: [paper: PaperOverview];
  refreshMetadata: [paper: PaperOverview];
}>();
const copied = shallowRef<string | null>(null);
const primaryEntry = computed(() => props.paper?.reading_entry);

async function copy(label: string, value: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(value);
    copied.value = `${label} 已复制`;
  } catch {
    copied.value = "无法访问剪贴板，请手动复制";
  }
  window.setTimeout(() => {
    copied.value = null;
  }, 1200);
}

function openReading(): void {
  if (!props.paper) return;
  emit("read", props.paper);
}
</script>

<template>
  <div class="overview-layer" :class="{ open }" @click.self="emit('close')">
    <aside class="overview" aria-label="论文概览" :aria-busy="loading">
      <header class="overview-heading">
        <strong>论文概览</strong
        ><button type="button" aria-label="关闭论文概览" @click="emit('close')">
          <BaseIcon name="close" />
        </button>
      </header>
      <div v-if="loading && !paper" class="overview-loading">
        <i></i><span></span><span></span><span></span>
      </div>
      <div v-else-if="error && !paper" class="overview-error" role="alert">
        <BaseIcon name="alert" /><b>概览暂时不可用</b>
        <p>{{ error }}</p>
        <button type="button" @click="emit('retry')">重试</button>
      </div>
      <template v-else-if="paper">
        <div class="overview-scroll">
          <section class="identity-section">
            <div class="paper-cover" aria-hidden="true">
              <b>MEDICAL<br />RESEARCH</b><i></i><i></i><i></i><i></i
              ><small>{{ paper.year ?? "—" }}</small>
            </div>
            <div class="identity-copy">
              <h2>{{ paper.title ?? "未命名论文" }}</h2>
              <p>{{ citationLine(paper) }}</p>
              <div class="identity-tags">
                <span v-if="paper.paper_type">{{ paper.paper_type }}</span
                ><span v-if="paper.journal_quartile">{{
                  paper.journal_quartile
                }}</span>
              </div>
            </div>
            <dl class="identifiers">
              <template v-if="paper.doi"
                ><dt>DOI</dt>
                <dd>
                  {{ paper.doi }}
                  <button
                    type="button"
                    :aria-label="`复制 DOI ${paper.doi}`"
                    @click="copy('DOI', paper.doi)"
                  >
                    ▣
                  </button>
                </dd></template
              >
              <template v-if="paper.pmid"
                ><dt>PMID</dt>
                <dd>
                  {{ paper.pmid }}
                  <button
                    type="button"
                    :aria-label="`复制 PMID ${paper.pmid}`"
                    @click="copy('PMID', paper.pmid)"
                  >
                    ▣
                  </button>
                </dd></template
              >
            </dl>
            <p v-if="copied" class="copy-state" role="status">{{ copied }}</p>
            <button
              v-if="paper.metadata_retryable"
              class="metadata-refresh"
              type="button"
              :disabled="actionPending"
              @click="emit('refreshMetadata', paper)"
            >
              <BaseIcon name="sync" />{{
                actionPending ? "正在更新…" : "补充论文元数据"
              }}
            </button>
          </section>
          <section class="work-section">
            <h3>论文工作</h3>
            <div class="metric-heading">
              <span>阅读进度</span><b>{{ paper.reading_progress_percent }}%</b>
            </div>
            <div class="progress-track">
              <i
                class="reading-bar"
                :style="{ width: `${paper.reading_progress_percent}%` }"
              ></i>
            </div>
            <div class="metric-caption">
              <span>{{
                paper.current_section ??
                (paper.reading_status === "read" ? "已完成" : "尚未开始")
              }}</span
              ><span>{{
                paper.reading_status === "reading"
                  ? "阅读中"
                  : paper.reading_status === "read"
                    ? "已阅读"
                    : "未阅读"
              }}</span>
            </div>
          </section>
          <section class="relations-section">
            <div class="section-title">
              <h3>关联研究</h3>
              <button type="button" @click="emit('editRelations', paper)">
                <BaseIcon name="plus" />关联研究
              </button>
            </div>
            <ul v-if="paper.relations.length">
              <li
                v-for="relation in paper.relations"
                :key="relation.research_context_id"
              >
                <span
                  class="role-dot"
                  :class="relation.role ?? 'to_evaluate'"
                ></span>
                <div>
                  <b>{{ relation.research_name }}</b
                  ><small>{{ roleLabel(relation.role) }}</small>
                </div>
                <span aria-hidden="true">›</span>
              </li>
            </ul>
            <p v-else class="section-empty">
              尚未关联研究。关联后可明确这篇论文在科研工作中的角色。
            </p>
          </section>
          <section class="activity-section">
            <div class="section-title"><h3>最近工作</h3></div>
            <ul v-if="paper.activities.length">
              <li
                v-for="activity in paper.activities.slice(0, 4)"
                :key="activity.id"
              >
                <span class="activity-mark">▣</span>
                <div>
                  <b>{{ relativeDate(activity.created_at) }}</b
                  ><small>{{ activityLabel(activity) }}</small>
                </div>
              </li>
            </ul>
            <p v-else class="section-empty">尚无真实工作记录</p>
          </section>
        </div>
        <footer class="overview-actions">
          <button
            class="overview-primary"
            type="button"
            :disabled="!primaryEntry?.enabled"
            :title="primaryEntry?.reason ?? undefined"
            @click="openReading"
          >
            {{
              primaryEntry ? entryLabel("reading", primaryEntry) : "开始阅读"
            }}
            <span>→</span>
          </button>
          <div>
            <button
              type="button"
              :disabled="!paper.document_id"
              @click="emit('resource', paper)"
            >
              查看对应资料
            </button>
          </div>
          <button
            class="overview-more"
            type="button"
            @click="emit('editRelations', paper)"
          >
            管理研究关联 <BaseIcon name="chevron-down" />
          </button>
        </footer>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.overview-layer {
  min-width: 0;
  border-left: 1px solid var(--line);
  background: #fff;
}
.overview {
  display: flex;
  height: 100%;
  min-width: 0;
  flex-direction: column;
  background: #fff;
}
.overview-heading {
  display: flex;
  height: 48px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border-bottom: 1px solid var(--line);
}
.overview-heading strong {
  font-size: 13px;
}
.overview-heading button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  background: transparent;
  color: #334155;
}
.overview-heading :deep(.icon) {
  width: 18px;
}
.overview-scroll {
  min-height: 0;
  flex: 1 1 auto;
  overflow: auto;
}
.overview-scroll section {
  padding: 16px 18px;
  border-bottom: 1px solid var(--line);
}
.identity-section {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 13px;
}
.paper-cover {
  position: relative;
  display: flex;
  width: 90px;
  height: 118px;
  flex-direction: column;
  padding: 13px 9px;
  border: 1px solid #e2e8f0;
  background: #fbfaf7;
  box-shadow: 0 3px 7px rgb(15 23 42 / 9%);
  color: #23314a;
}
.paper-cover b {
  font-family: Georgia, serif;
  font-size: 7px;
  line-height: 1.25;
  text-align: center;
}
.paper-cover i {
  display: block;
  height: 2px;
  margin-top: 7px;
  background: #cbd5e1;
}
.paper-cover i:nth-of-type(2) {
  width: 78%;
}
.paper-cover i:nth-of-type(3) {
  width: 88%;
}
.paper-cover small {
  position: absolute;
  right: 8px;
  bottom: 8px;
  color: #64748b;
  font-size: 8px;
}
.identity-copy {
  min-width: 0;
}
.identity-copy h2 {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: #0f172a;
  font-size: 13.5px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}
.identity-copy p {
  margin: 7px 0;
  color: #52627a;
  font-size: 11.5px;
  line-height: 1.55;
}
.identity-tags {
  display: flex;
  gap: 6px;
}
.identity-tags span {
  border-radius: 3px;
  padding: 2px 5px;
  background: #eaf2ff;
  color: #0b5fcc;
  font-size: 10px;
  font-weight: 700;
}
.identity-tags span + span {
  background: #f1edff;
  color: #6d28d9;
}
.identifiers {
  display: grid;
  grid-column: 1/-1;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 7px 8px;
  margin: 3px 0 0;
  color: #52627a;
  font-size: 10.5px;
}
.identifiers dt {
  font-weight: 600;
}
.identifiers dd {
  overflow: hidden;
  margin: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.identifiers button {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 10px;
}
.copy-state {
  grid-column: 1/-1;
  margin: 0;
  color: #087a55;
  font-size: 10.5px;
}
.metadata-refresh {
  display: flex;
  grid-column: 1/-1;
  min-height: 30px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid #dbe5f2;
  border-radius: 4px;
  background: #fff;
  color: #0b5fcc;
  font: inherit;
  font-size: 11px;
}
.metadata-refresh :deep(.icon) {
  width: 13px;
}
.work-section h3,
.section-title h3 {
  margin: 0;
  color: #0f172a;
  font-size: 13px;
}
.metric-heading,
.metric-caption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 13px;
  color: #52627a;
  font-size: 11.5px;
}
.metric-heading b {
  color: #0f172a;
  font-size: 12px;
}
.analysis-heading {
  margin-top: 17px;
}
.progress-track {
  height: 5px;
  margin-top: 7px;
  border-radius: 5px;
  background: #e8edf4;
  overflow: hidden;
}
.progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
}
.reading-bar {
  background: #18a568;
}
.analysis-bar {
  background: #8b5cf6;
}
.metric-caption {
  margin-top: 6px;
  color: #64748b;
  font-size: 10.5px;
}
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title button {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 0;
  background: transparent;
  color: #0b5fcc;
  font: inherit;
  font-size: 11px;
  font-weight: 650;
}
.section-title button :deep(.icon) {
  width: 13px;
}
.relations-section ul,
.activity-section ul {
  display: grid;
  gap: 11px;
  margin: 13px 0 0;
  padding: 0;
  list-style: none;
}
.relations-section li,
.activity-section li {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  color: #334155;
}
.relations-section li > div,
.activity-section li > div {
  display: grid;
  min-width: 0;
  gap: 1px;
}
.relations-section li b,
.activity-section li b {
  overflow: hidden;
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.relations-section li small,
.activity-section li small {
  color: #64748b;
  font-size: 10.5px;
}
.relations-section li > span:last-child {
  margin-left: auto;
  color: #64748b;
}
.role-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  margin-top: 5px;
  border-radius: 50%;
  background: #94a3b8;
}
.role-dot.core_evidence {
  background: #ef3b4e;
}
.role-dot.background_support {
  background: #f59e0b;
}
.role-dot.method_reference {
  background: #2563eb;
}
.role-dot.supplementary_reading {
  background: #18a568;
}
.activity-mark {
  display: grid;
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid #0b5fcc;
  border-radius: 3px;
  color: #0b5fcc;
  font-size: 6px;
}
.section-empty {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 11px;
  line-height: 1.55;
}
.overview-actions {
  display: grid;
  flex: 0 0 auto;
  gap: 8px;
  padding: 12px 18px 16px;
  border-top: 1px solid var(--line);
  background: #fff;
}
.overview-actions button {
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: #fff;
  color: #0b5fcc;
  font: inherit;
  font-size: 11.5px;
  font-weight: 700;
}
.overview-actions button:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}
.overview-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-color: #0b5fcc !important;
  background: #0b5fcc !important;
  color: #fff !important;
}
.overview-actions > div {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.overview-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.overview-more :deep(.icon) {
  width: 12px;
}
.overview-loading {
  display: grid;
  gap: 13px;
  padding: 18px;
}
.overview-loading i,
.overview-loading span {
  display: block;
  border-radius: 5px;
  background: #edf2f7;
}
.overview-loading i {
  width: 100%;
  height: 125px;
}
.overview-loading span {
  height: 90px;
}
.overview-error {
  display: grid;
  place-items: center;
  padding: 48px 22px;
  text-align: center;
}
.overview-error :deep(.icon) {
  width: 30px;
  height: 30px;
  color: #b54708;
}
.overview-error b {
  margin-top: 12px;
}
.overview-error p {
  color: #64748b;
  font-size: 12px;
}
.overview-error button {
  border: 1px solid #0b5fcc;
  border-radius: 4px;
  padding: 6px 12px;
  background: #fff;
  color: #0b5fcc;
  font: inherit;
}
@media (max-width: 1023px) {
  .overview-layer {
    position: fixed;
    z-index: 44;
    inset: 0;
    display: none;
    border: 0;
    background: rgb(15 23 42 / 28%);
  }
  .overview-layer.open {
    display: block;
  }
  .overview {
    width: min(368px, calc(100vw - 44px));
    margin-left: auto;
    box-shadow: -8px 0 24px rgb(15 23 42 / 10%);
  }
}
@media (max-width: 767px) {
  .overview-layer.open {
    display: flex;
    align-items: flex-end;
  }
  .overview {
    width: 100%;
    max-height: 88vh;
    margin: 0;
    border-radius: 10px 10px 0 0;
  }
  .overview-heading {
    height: 52px;
  }
  .overview-scroll {
    overscroll-behavior: contain;
  }
}
</style>
