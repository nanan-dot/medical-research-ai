<script setup lang="ts">
import { computed, onScopeDispose, shallowRef, watch } from "vue";

import {
  medicalTranslationsApi,
  type TranslationRevision,
  type TranslationSegmentStatus,
} from "../../api/medicalTranslations";
import {
  readPageTranslationSegments,
  type TranslationReadingSegment,
} from "../../api/readingSegments";

const props = defineProps<{
  bootstrap: {
    paper: { document_id: number };
    document: { file_hash: string };
    revision_fence: {
      anchor_revision_id: number | null;
      segmentation_revision_id: number | null;
    };
  };
  currentPage: number;
  mode: "bilingual" | "translated";
}>();
const emit = defineEmits<{ locateSourceAnchor: [anchorId: number] }>();

const segments = shallowRef<TranslationReadingSegment[]>([]);
const statuses = shallowRef(new Map<number, TranslationSegmentStatus>());
const loading = shallowRef(false);
const error = shallowRef<string | null>(null);
let generation = 0;
let controller: AbortController | null = null;
let pollTimer: ReturnType<typeof setTimeout> | null = null;
let pollFailures = 0;

const renderedSegments = computed(() => segments.value.map((segment) => ({
  segment,
  status: statuses.value.get(segment.id) ?? null,
  revision: statuses.value.get(segment.id)?.revision ?? null,
})));

function replaceStatus(status: TranslationSegmentStatus): void {
  statuses.value = new Map(statuses.value).set(status.segment_id, status);
}

async function refreshActiveJobs(current: number): Promise<void> {
  const active = [...statuses.value.values()].filter((item) =>
    item.job && ["queued", "running", "quality_checking"].includes(item.job.state),
  );
  if (!active.length || current !== generation) return;
  try {
    await Promise.all(active.map(async (item) => {
    const job = await medicalTranslationsApi.job(item.job!.id);
    if (current !== generation) return;
    let revision: TranslationRevision | null = item.revision;
    if (job.state === "succeeded" && job.result_revision_id !== null) {
      revision = await medicalTranslationsApi.revision(job.result_revision_id);
    }
    if (current === generation) {
      const state: TranslationSegmentStatus["state"] = revision
        ? "cached"
        : ["queued", "running", "quality_checking"].includes(job.state)
          ? job.state === "queued" ? "queued" : "running"
          : "degraded";
      replaceStatus({
        ...item,
        state,
        job,
        revision,
        degraded_reason: state === "degraded"
          ? job.error_message ?? job.error_code ?? "translation_failed"
          : item.degraded_reason,
      });
    }
    }));
    pollFailures = 0;
  } catch (cause) {
    if (current !== generation) return;
    pollFailures += 1;
    error.value = cause instanceof Error
      ? `译文状态刷新失败，正在自动重试：${cause.message}`
      : "译文状态刷新失败，正在自动重试";
  }
  if (
    current === generation
    && [...statuses.value.values()].some((item) =>
      item.job && ["queued", "running", "quality_checking"].includes(item.job.state),
    )
  ) {
    const delay = Math.min(5_000, 800 * 2 ** pollFailures);
    pollTimer = setTimeout(() => void refreshActiveJobs(current), delay);
  }
}

async function load(): Promise<void> {
  const anchorRevisionId = props.bootstrap.revision_fence.anchor_revision_id;
  const segmentationRevisionId = props.bootstrap.revision_fence.segmentation_revision_id;
  const current = ++generation;
  controller?.abort();
  controller = new AbortController();
  if (pollTimer !== null) clearTimeout(pollTimer);
  pollTimer = null;
  segments.value = [];
  statuses.value = new Map();
  error.value = null;
  pollFailures = 0;
  if (anchorRevisionId === null || segmentationRevisionId === null) {
    error.value = "论文原文结构仍在后台处理中，暂时无法显示双语页面。";
    return;
  }
  loading.value = true;
  try {
    const nextSegments = await readPageTranslationSegments(
      props.bootstrap.paper.document_id,
      props.currentPage,
      {
        expected_file_hash: props.bootstrap.document.file_hash,
        expected_anchor_revision_id: anchorRevisionId,
        expected_segmentation_revision_id: segmentationRevisionId,
      },
      controller.signal,
    );
    if (current !== generation) return;
    segments.value = nextSegments;
    for (let offset = 0; offset < nextSegments.length; offset += 12) {
      const batch = nextSegments.slice(offset, offset + 12);
      const intent = await medicalTranslationsApi.requestSegments(
        props.bootstrap.paper.document_id,
        {
          expected_file_hash: props.bootstrap.document.file_hash,
          expected_anchor_revision_id: anchorRevisionId,
          expected_segmentation_revision_id: segmentationRevisionId,
          segment_ids: batch.map((segment) => segment.id),
          active_segment_id: null,
          trigger: "visible",
        },
        controller.signal,
      );
      if (current !== generation) return;
      statuses.value = new Map([
        ...statuses.value,
        ...intent.items.map((item) => [item.segment_id, item] as const),
      ]);
    }
    await refreshActiveJobs(current);
  } catch (cause) {
    if (!controller.signal.aborted && current === generation) {
      error.value = cause instanceof Error ? cause.message : "双语页面加载失败";
    }
  } finally {
    if (current === generation) loading.value = false;
  }
}

watch(
  () => [
    props.bootstrap.paper.document_id,
    props.bootstrap.document.file_hash,
    props.bootstrap.revision_fence.anchor_revision_id,
    props.bootstrap.revision_fence.segmentation_revision_id,
    props.currentPage,
  ],
  () => void load(),
  { immediate: true },
);
onScopeDispose(() => {
  generation += 1;
  controller?.abort();
  if (pollTimer !== null) clearTimeout(pollTimer);
});
</script>

<template>
  <section class="translated-canvas" :aria-busy="loading" aria-label="论文译文阅读">
    <p v-if="loading && !segments.length" class="state" role="status">正在读取第 {{ currentPage }} 页译文…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <article
      v-for="item in renderedSegments"
      :key="item.segment.id"
      class="translated-segment"
      :data-quality="item.revision?.quality_status ?? 'pending'"
    >
      <p v-if="mode === 'bilingual' || item.revision?.quality_status === 'blocked'" class="source-text">
        {{ item.segment.text }}
      </p>
      <div class="translation-column">
        <p v-if="item.revision?.quality_status === 'blocked'" class="blocked" role="alert">
          该段译文触发医学质量门禁，请核对原文。
        </p>
        <p v-else-if="item.revision" class="translated-text">{{ item.revision.translated_text }}</p>
        <p v-else-if="item.status?.state === 'degraded'" class="state">此段原文质量不足，暂不自动翻译。</p>
        <p v-else class="state" role="status">译文正在后台准备…</p>
        <button
          v-if="item.revision"
          type="button"
          class="locate"
          @click="emit('locateSourceAnchor', item.revision.source_anchor_id)"
        >
          回到原文
        </button>
      </div>
    </article>
    <p v-if="!loading && !error && !segments.length" class="state">本页没有可翻译的正文段落。</p>
  </section>
</template>

<style scoped>
.translated-canvas { height: calc(100vh - 150px); overflow: auto; padding: 24px clamp(16px, 4vw, 56px); background: #eef3f9; }
.translated-segment { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); max-width: 980px; margin: 0 auto 12px; border: 1px solid #dce4f0; border-radius: 8px; background: #fff; box-shadow: 0 2px 8px rgb(17 24 39 / 5%); }
.translated-segment[data-quality="blocked"] { border-color: #f3b4ad; }
.source-text, .translation-column { min-width: 0; margin: 0; padding: 16px 18px; font-size: 14px; line-height: 1.75; }
.source-text { border-right: 1px solid #e5eaf2; color: #344054; }
.translation-column { color: #111827; }
.translated-text, .blocked, .state { margin: 0; white-space: pre-wrap; }
.state { color: #667085; }
.error, .blocked { color: #b42318; }
.locate { margin-top: 10px; border: 0; padding: 0; background: transparent; color: #0868f7; font: inherit; font-weight: 700; cursor: pointer; }
.locate:focus-visible { outline: 2px solid #0868f7; outline-offset: 3px; }
.translated-canvas:has(.translated-segment) > .state { max-width: 980px; margin-inline: auto; }
.translated-canvas .translated-segment:has(.source-text) .translation-column { display: block; }
.translated-canvas .translated-segment:not(:has(.source-text)) { grid-template-columns: 1fr; }
@media (max-width: 720px) { .translated-segment { grid-template-columns: 1fr; }.source-text { border-right: 0; border-bottom: 1px solid #e5eaf2; }.translated-canvas { height: auto; min-height: 55vh; padding: 12px; } }
@media (prefers-reduced-motion: reduce) { .translated-canvas { scroll-behavior: auto; } }
</style>
