<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { DocumentRecord } from "../../api/documents";
import type { TranslationJobState } from "../../api/medicalTranslations";
import { useMedicalTranslation } from "../../composables/useMedicalTranslation";
import { useSegmentTranslationIntent } from "../../composables/useSegmentTranslationIntent";
import type { PdfTextSelection } from "../../types/documentAnnotations";
import type { VisibleReadingContext } from "../../types/readingContext";
import { createTranslationFollowPolicy } from "../../utils/translationFollowPolicy";
import BilingualTranslationView from "./BilingualTranslationView.vue";

const props = withDefaults(defineProps<{ document: Pick<DocumentRecord, "id" | "file_hash">; selection: PdfTextSelection | null; readingContext?: VisibleReadingContext | null }>(), {
  readingContext: null,
});
const emit = defineEmits<{ revisionConflict: []; locateSourceAnchor: [anchorId: number] }>();
const preferenceKey = computed(() => `medical-translation-ui:${props.document.id}`);
const followEnabled = ref(true);
const pinnedSegmentId = ref<number | null>(null);
const displayMode = ref<"source" | "bilingual">("source");
const followedSegmentId = ref<number | null>(null);
const followPolicy = createTranslationFollowPolicy({ dwellMs: 300 });
const correction = ref("");
const reason = ref("");
const translation = useMedicalTranslation(
  () => props.document.id,
  () => props.document.file_hash,
  () => props.selection,
);
const segmentIntent = useSegmentTranslationIntent({
  documentId: () => props.document.id,
  fileHash: () => props.document.file_hash,
  context: () => props.readingContext,
  followEnabled: () => followEnabled.value,
  pinnedSegmentId: () => pinnedSegmentId.value,
  hasSelection: () => Boolean(props.selection),
  isEditing: () => translation.editing.value,
});
const blockingCount = computed(() => translation.revision.value?.issues.filter((issue) => issue.blocking).length ?? 0);
const unresolvedCount = computed(() => translation.revision.value?.terms.filter((term) => term.status !== "matched").length ?? 0);
const statusLabels: Record<TranslationJobState, string> = {
  queued: "翻译已排队",
  running: "正在生成译文",
  quality_checking: "正在核对医学数字与术语",
  succeeded: "翻译处理完成",
  failed: "翻译未完成",
  cancelled: "翻译已取消",
};
const statusText = computed(() => translation.job.value ? statusLabels[translation.job.value.state] : "");

function restorePreferences(): void {
  try {
    const saved = JSON.parse(localStorage.getItem(preferenceKey.value) ?? "{}") as Record<string, unknown>;
    followEnabled.value = saved.followEnabled !== false;
    pinnedSegmentId.value = typeof saved.pinnedSegmentId === "number" ? saved.pinnedSegmentId : null;
    displayMode.value = saved.displayMode === "bilingual" ? "bilingual" : "source";
  } catch { followEnabled.value = true; pinnedSegmentId.value = null; displayMode.value = "source"; }
}

function persistPreferences(): void {
  // 仅保存界面状态和段落标识，译文与原文不会进入 localStorage。
  localStorage.setItem(preferenceKey.value, JSON.stringify({ followEnabled: followEnabled.value,
    pinnedSegmentId: pinnedSegmentId.value, displayMode: displayMode.value }));
}

watch(() => [props.document.id, props.document.file_hash], () => {
  restorePreferences();
  followPolicy.setGeneration(`${props.document.id}:${props.document.file_hash}`);
  followedSegmentId.value = null;
}, { immediate: true });

watch(() => props.readingContext, context => {
  if (!followEnabled.value || !context) return;
  followPolicy.setGeneration(`${context.documentId}:${context.anchorRevisionId}:${context.segmentationRevisionId}`);
  followedSegmentId.value = followPolicy.observe({ segmentId: context.primarySegmentId, now: performance.now(),
    hasSelection: Boolean(props.selection), isEditing: translation.editing.value, pinnedSegmentId: pinnedSegmentId.value });
}, { immediate: true });

watch(() => segmentIntent.result.value, intent => {
  if (props.selection || !intent || segmentIntent.activeSegmentId.value === null) return;
  const active = intent.items.find(item => item.segment_id === segmentIntent.activeSegmentId.value);
  if (active?.job) void translation.openJob(active.job);
});

watch(() => segmentIntent.activeSegmentId.value, segmentId => {
  if (segmentId !== null) followedSegmentId.value = segmentId;
});

watch([followEnabled, pinnedSegmentId, displayMode], persistPreferences);

watch(() => translation.revision.value?.id, () => {
  correction.value = translation.revision.value?.translated_text ?? "";
  reason.value = "";
});

async function save(): Promise<void> {
  const saved = await translation.saveCorrection(correction.value, reason.value.trim() || null);
  if (!saved && translation.error.value?.includes("changed")) emit("revisionConflict");
}
</script>

<template>
  <section class="translation-panel" aria-labelledby="medical-translation-title">
    <header class="panel-heading">
      <div>
        <p class="eyebrow">Selection / EN → ZH-CN</p>
        <h2 id="medical-translation-title">医学选区翻译</h2>
      </div>
      <span v-if="translation.revision.value" class="quality" :data-status="translation.revision.value.quality_status">
        {{ translation.revision.value.quality_status === "machine_checked" ? "机器核对通过" : translation.revision.value.quality_status === "human_reviewed" ? "人工修订" : translation.revision.value.quality_status === "blocked" ? "已阻断" : "需要复核" }}
      </span>
    </header>

    <div class="follow-controls" aria-label="翻译阅读模式">
      <label><input v-model="followEnabled" type="checkbox" /> 跟随阅读</label>
      <button type="button" class="secondary" :aria-pressed="pinnedSegmentId !== null"
        :disabled="!followedSegmentId && pinnedSegmentId === null"
        @click="pinnedSegmentId = pinnedSegmentId === null ? followedSegmentId : null">
        {{ pinnedSegmentId === null ? "固定当前段" : "取消固定" }}
      </button>
      <select v-model="displayMode" aria-label="译文显示模式">
        <option value="source">原文模式</option><option value="bilingual">双语对照</option>
      </select>
    </div>
    <p v-if="followEnabled && followedSegmentId" class="status" role="status" aria-live="polite">
      正在跟随稳定段落 #{{ followedSegmentId }}{{ pinnedSegmentId ? "（已固定）" : "" }}
    </p>
    <p v-if="segmentIntent.error.value" class="error" role="alert">{{ segmentIntent.error.value }}</p>
    <p v-if="segmentIntent.result.value?.items.some(item => item.state === 'degraded')" class="status" role="status">
      部分可见段落不适合自动翻译，已保留原文并标记复核。
    </p>

    <div v-if="!props.selection && !followedSegmentId" class="empty-state">
      <strong>先在 PDF 中选中文字</strong>
      <p>译文会绑定到同一原文锚点，重新打开后仍可回到原文。</p>
    </div>
    <div v-else-if="!props.selection && followedSegmentId" class="empty-state">
      <strong>正在翻译当前稳定段落</strong>
      <p>PDF 中央区域保持原文；段落 #{{ followedSegmentId }} 的译文会在此处更新。</p>
    </div>
    <div v-else-if="!props.selection?.anchorDescriptor" class="empty-state" role="alert">
      <strong>当前选区不能建立稳定锚点</strong>
      <p>请在可选择的 PDF 文本层重新框选。</p>
    </div>
    <template v-else>
      <blockquote class="source-quote">{{ props.selection?.selectedText }}</blockquote>
      <div class="actions">
        <button v-if="!translation.job.value" type="button" class="primary" :disabled="!translation.canTranslate.value" @click="translation.translate">翻译此选区</button>
        <button v-if="translation.job.value && ['queued', 'running', 'quality_checking'].includes(translation.job.value.state)" type="button" class="secondary" @click="translation.cancel">取消</button>
        <button v-if="translation.job.value && ['failed', 'cancelled'].includes(translation.job.value.state)" type="button" class="primary" @click="translation.retry">重试翻译</button>
      </div>
    </template>

    <p v-if="statusText" class="status" role="status" aria-live="polite" aria-atomic="true">{{ statusText }}</p>
    <p v-if="translation.error.value" class="error" role="alert">{{ translation.error.value }}</p>

    <article v-if="translation.revision.value" class="translation-result" aria-label="翻译结果">
      <div v-if="translation.revision.value.quality_status === 'blocked'" class="blocked" role="alert">
        译文存在 {{ blockingCount }} 项阻断问题，不应直接用于医学判断。
      </div>
      <BilingualTranslationView v-if="!translation.editing.value" :source-quote="props.selection?.selectedText ?? '当前稳定段落原文由 PDF 保持显示'" :revision="translation.revision.value" :mode="displayMode" @locate="emit('locateSourceAnchor', translation.revision.value.source_anchor_id)" />
      <form v-else class="correction-form" @submit.prevent="save">
        <label for="translation-correction">人工修订译文</label>
        <textarea id="translation-correction" v-model="correction" rows="7" required :aria-invalid="!correction.trim()" />
        <label for="translation-reason">修订说明（可选）</label>
        <input id="translation-reason" v-model="reason" maxlength="1000" />
        <div class="actions"><button class="primary" type="submit" :disabled="translation.busy.value || !correction.trim()">保存为新版本</button><button class="secondary" type="button" @click="translation.editing.value = false">取消编辑</button></div>
      </form>
      <button v-if="!translation.editing.value" type="button" class="text-action" @click="translation.editing.value = true">人工修订</button>

      <dl class="quality-grid">
        <div><dt>数字检查</dt><dd>{{ blockingCount ? `${blockingCount} 项阻断` : "未发现变化" }}</dd></div>
        <div><dt>术语状态</dt><dd>{{ unresolvedCount ? `${unresolvedCount} 项待确认` : "本地规则已核对" }}</dd></div>
        <div><dt>对齐片段</dt><dd>{{ translation.revision.value.alignment.length }}</dd></div>
        <div><dt>版本</dt><dd>v{{ translation.revision.value.version }}</dd></div>
      </dl>

      <details v-if="translation.revision.value.issues.length" class="evidence-list">
        <summary>质量问题（{{ translation.revision.value.issues.length }}）</summary>
        <ul><li v-for="issue in translation.revision.value.issues" :key="`${issue.code}-${issue.source_span}`"><strong>{{ issue.code }}</strong>：{{ issue.message }}</li></ul>
      </details>
      <details v-if="translation.revision.value.terms.length" class="evidence-list">
        <summary>术语证据（{{ translation.revision.value.terms.length }}）</summary>
        <ul><li v-for="term in translation.revision.value.terms" :key="`${term.source_term}-${term.source_span}`"><strong>{{ term.source_term }}</strong> · {{ term.status }} · {{ term.provenance }}</li></ul>
      </details>
      <p class="disclaimer">机器核对不等于医学专家审核。请结合原文和专业判断使用。</p>
    </article>
  </section>
</template>

<style scoped>
.translation-panel { display: grid; gap: .9rem; color: var(--text-primary); }
.panel-heading { display: flex; align-items: start; justify-content: space-between; gap: .75rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: .75rem; }
.eyebrow { margin: 0 0 .2rem; color: var(--text-muted); font: 700 .66rem/1.2 ui-monospace, monospace; letter-spacing: .1em; text-transform: uppercase; }
h2 { margin: 0; font-size: 1rem; letter-spacing: -.01em; }
.quality { border: 1px solid var(--border-subtle); border-radius: 999px; padding: .22rem .5rem; color: var(--text-muted); font-size: .7rem; font-weight: 750; white-space: nowrap; }
.quality[data-status="blocked"] { border-color: color-mix(in srgb, var(--color-danger) 45%, transparent); color: var(--color-danger); }
.empty-state { border-left: 3px solid var(--color-primary); padding: .2rem 0 .2rem .8rem; }.empty-state strong { font-size: .88rem; }.empty-state p { margin: .25rem 0 0; color: var(--text-muted); font-size: .8rem; line-height: 1.55; }
.source-quote { max-height: 8rem; overflow: auto; margin: 0; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: .75rem; background: color-mix(in srgb, var(--color-primary) 4%, var(--paper)); font-size: .82rem; line-height: 1.55; }
.actions { display: flex; flex-wrap: wrap; gap: .5rem; }.actions button, .text-action { min-height: 2.25rem; border-radius: var(--radius-sm); padding: .45rem .7rem; font: inherit; font-size: .8rem; font-weight: 750; cursor: pointer; }.primary { border: 1px solid var(--color-primary); background: var(--color-primary); color: white; }.secondary { border: 1px solid var(--border-subtle); background: var(--paper); color: var(--text-primary); }.text-action { justify-self: start; border: 0; padding-inline: 0; background: transparent; color: var(--color-primary); }
.follow-controls { display: flex; flex-wrap: wrap; align-items: center; gap: .55rem; }.follow-controls label { display: flex; align-items: center; gap: .35rem; font-size: .8rem; font-weight: 700; }.follow-controls select { min-height: 2.25rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); background: var(--paper); color: var(--text-primary); padding: .4rem; }
button:disabled { cursor: not-allowed; opacity: .55; }.translation-panel button:focus-visible, textarea:focus-visible, input:focus-visible, summary:focus-visible { outline: 3px solid color-mix(in srgb, var(--color-primary) 42%, transparent); outline-offset: 2px; }
.status, .error, .disclaimer { margin: 0; font-size: .78rem; line-height: 1.5; }.status, .disclaimer { color: var(--text-muted); }.error { color: var(--color-danger); }.blocked { border-left: 3px solid var(--color-danger); padding: .55rem .7rem; background: color-mix(in srgb, var(--color-danger) 7%, var(--paper)); color: var(--color-danger); font-size: .78rem; }
.translation-result { display: grid; gap: .8rem; }.translated-text { margin: 0; white-space: pre-wrap; font-size: .92rem; line-height: 1.75; }
.correction-form { display: grid; gap: .4rem; }.correction-form label { font-size: .75rem; font-weight: 750; }.correction-form textarea, .correction-form input { width: 100%; box-sizing: border-box; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: .6rem; background: var(--paper); color: var(--text-primary); font: inherit; font-size: .82rem; resize: vertical; }
.quality-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; border: 1px solid var(--border-subtle); }.quality-grid div { padding: .55rem .65rem; border-right: 1px solid var(--border-subtle); border-bottom: 1px solid var(--border-subtle); }.quality-grid div:nth-child(2n) { border-right: 0; }.quality-grid div:nth-last-child(-n+2) { border-bottom: 0; }.quality-grid dt { color: var(--text-muted); font-size: .68rem; }.quality-grid dd { margin: .15rem 0 0; font: 750 .78rem/1.3 ui-monospace, monospace; }
.evidence-list { font-size: .78rem; }.evidence-list summary { cursor: pointer; font-weight: 750; }.evidence-list ul { display: grid; gap: .35rem; margin: .5rem 0 0; padding-left: 1.1rem; line-height: 1.45; }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; transition: none !important; } }
</style>
