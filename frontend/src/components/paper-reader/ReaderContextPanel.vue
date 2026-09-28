<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";
import { ApiError } from "../../api/client";
import {
  paperReaderApi,
  type ReaderBootstrap,
  type ReaderMessage,
  type ReaderTab,
  type ReaderRecord,
} from "../../api/paperReader";
import ReaderRecordsModal from "./ReaderRecordsModal.vue";
import MedicalTranslationPanel from "../document/MedicalTranslationPanel.vue";
import type { PdfTextSelection } from "../../types/documentAnnotations";
const props = defineProps<{
  bootstrap: ReaderBootstrap;
  selection: PdfTextSelection | null;
}>();
const emit = defineEmits<{
  locate: [record: ReaderRecord];
  locateSourceAnchor: [anchorId: number];
}>();
const tab = shallowRef<ReaderTab>(props.bootstrap.preference.right_panel_tab);
const summary = shallowRef(props.bootstrap.record_counts);
const records = shallowRef<readonly ReaderRecord[]>([]);
const recordsOpen = shallowRef(false);
const recordsType = shallowRef<string | null>(null);
defineExpose({ refresh: loadRecords, openTranslation });
const question = shallowRef("");
const messages = shallowRef<ReaderMessage[]>([]);
const conversationId = shallowRef<number | null>(null);
const sending = shallowRef(false);
const error = shallowRef<string | null>(null);
const translationUnavailable = computed(
  () => props.bootstrap.capabilities.translation !== "available",
);
const isConversationMode = shallowRef(false);
const assistantActions = computed(() => [
  {
    key: "explain",
    icon: "◇",
    label: "解释当前段落",
    description: "结合原文上下文进行专业解释",
    prompt: "请解释当前页面的核心段落，并指出对应原文位置。",
  },
  {
    key: "summary",
    icon: "▤",
    label: "总结本章节",
    description: "快速概括章节主要内容",
    prompt: "请总结当前章节的研究内容和关键结论。",
  },
  {
    key: "analysis",
    icon: "◎",
    label: "分析研究结果",
    description: "分析结果的意义和临床价值",
    prompt: "请分析本文研究结果的意义、局限与临床价值。",
  },
  {
    key: "question",
    icon: "⌁",
    label: "回答论文问题",
    description: "基于论文内容回答你的问题",
    prompt: "请基于本文证据回答：",
  },
  {
    key: "notes",
    icon: "□",
    label: "生成阅读笔记",
    description: "生成结构化的阅读笔记",
    prompt: "请生成一份结构化阅读笔记，包含方法、结果、结论和局限。",
  },
]);
async function loadRecords(): Promise<void> {
  try {
    const [nextSummary, list] = await Promise.all([
      paperReaderApi.recordSummary(props.bootstrap.paper.document_id),
      paperReaderApi.records(props.bootstrap.paper.document_id),
    ]);
    summary.value = nextSummary;
    records.value = list.items;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取我的记录";
  }
}
async function ensureConversation(): Promise<void> {
  if (conversationId.value) return;
  try {
    const conversation = await paperReaderApi
      .latestConversation(props.bootstrap.paper.document_id)
      .catch(() =>
        paperReaderApi.createConversation(props.bootstrap.paper.document_id),
      );
    conversationId.value = conversation.id;
    messages.value = [...conversation.messages];
  } catch (cause) {
    error.value =
      cause instanceof Error ? cause.message : "无法启动 SW Copilot";
  }
}
async function ask(): Promise<void> {
  if (!question.value.trim() || !conversationId.value || sending.value) return;
  sending.value = true;
  isConversationMode.value = true;
  error.value = null;
  const text = question.value.trim();
  question.value = "";
  try {
    const readerContext = props.bootstrap.revision_fence.anchor_revision_id
      ? {
          document_id: props.bootstrap.paper.document_id,
          expected_anchor_revision_id:
            props.bootstrap.revision_fence.anchor_revision_id,
          expected_segmentation_revision_id:
            props.bootstrap.revision_fence.segmentation_revision_id,
        }
      : {};
    let answer: ReaderMessage;
    try {
      answer = await paperReaderApi.ask(conversationId.value, text, {
        ...readerContext,
      });
    } catch (cause) {
      // The reader can stay open while its conversation is cleared elsewhere.
      // Rebind to a fresh conversation instead of surfacing a stale-id error.
      if (!(cause instanceof ApiError) || cause.status !== 404) throw cause;
      conversationId.value = null;
      messages.value = [];
      await ensureConversation();
      if (!conversationId.value) throw cause;
      answer = await paperReaderApi.ask(conversationId.value, text, {
        ...readerContext,
      });
    }
    messages.value = [...messages.value, answer];
  } catch (cause) {
    isConversationMode.value = false;
    question.value = text;
    error.value = cause instanceof Error ? cause.message : "提问失败";
  } finally {
    sending.value = false;
  }
}
function chooseAction(prompt: string): void {
  question.value = prompt;
  void ensureConversation();
}
function switchTab(next: ReaderTab): void {
  tab.value = next;
  if (next === "copilot") void ensureConversation();
}
function openTranslation(): void {
  tab.value = "translation";
}
function openRecords(type: string | null = null): void { recordsType.value = type; recordsOpen.value = true; }
function closeRecords(): void { recordsOpen.value = false; }
function locateRecord(record: ReaderRecord): void { emit("locate", record); closeRecords(); }
onMounted(() => {
  void loadRecords();
  if (tab.value === "copilot") void ensureConversation();
});
</script>
<template>
  <aside class="context" aria-label="我的记录与 SW Copilot">
    <section class="records">
      <header>
        <h2>我的记录</h2>
        <button type="button" @click="openRecords()">全部记录 <span aria-hidden="true">›</span></button>
      </header>
      <div class="counts">
        <button class="count count-highlight" type="button" @click="openRecords('highlight')"><i aria-hidden="true">★</i><em>高亮</em><b>{{ summary.highlights }}</b></button>
        <button class="count count-note" type="button" @click="openRecords('annotation')"><i aria-hidden="true">✎</i><em>批注</em><b>{{ summary.annotations }}</b></button>
        <button class="count count-question" type="button" @click="openRecords('question')"><i aria-hidden="true">?</i><em>疑问</em><b>{{ summary.questions }}</b></button>
        <button class="count count-bookmark" type="button" @click="openRecords('bookmark')"><i aria-hidden="true">▮</i><em>收藏</em><b>{{ summary.bookmarks }}</b></button>
      </div>
      <ReaderRecordsModal :open="recordsOpen" :records="records" :active-type="recordsType" @close="closeRecords" @locate="locateRecord" />
    </section>
    <section class="panel assistant-panel">
      <div class="tabs" role="tablist" aria-label="阅读辅助">
        <button
          role="tab"
          :aria-selected="tab === 'translation'"
          @click="switchTab('translation')"
        >
          实时翻译
        </button>
        <button
          role="tab"
          :aria-selected="tab === 'copilot'"
          @click="switchTab('copilot')"
        >
          SW Copilot
        </button>
      </div>
      <MedicalTranslationPanel
        v-if="tab === 'translation' && !translationUnavailable"
        class="translation-content"
        :document="{
          id: bootstrap.paper.document_id,
          file_hash: bootstrap.document.file_hash,
        }"
        :selection="selection"
        @locate-source-anchor="emit('locateSourceAnchor', $event)"
      />
      <div v-else-if="tab === 'translation'" class="translation-empty" role="status">
        <span aria-hidden="true">译</span><b>翻译服务未启用</b>
        <p v-if="translationUnavailable">
          当前论文仍可阅读、批注和使用 SW
          Copilot；双语、中文及选区翻译暂不可用。
        </p>
      </div>
      <header v-else-if="!isConversationMode" class="assistant-header">
        <span class="assistant-mark" aria-hidden="true">◉</span>
        <h2>AI阅读助手</h2>
      </header>
      <div
        v-if="tab === 'copilot'"
        class="copilot"
        :class="{ 'copilot--conversation': isConversationMode }"
      >
        <template v-if="!isConversationMode">
          <p class="context-line">当前页面：第 {{ bootstrap.resume.page }} 页</p>
          <h3>我可以帮助你：</h3>
          <div class="assistant-actions">
            <button
              v-for="action in assistantActions"
              :key="action.key"
              type="button"
              @click="chooseAction(action.prompt)"
            >
              <i aria-hidden="true">{{ action.icon }}</i
              ><span
                ><b>{{ action.label }}</b
                ><small>{{ action.description }}</small></span
              >
            </button>
          </div>
        </template>
        <div
          v-if="isConversationMode"
          class="messages"
          :class="{ 'messages--conversation': isConversationMode }"
          aria-live="polite"
        >
          <article
            v-for="message in messages"
            :key="message.id"
            :class="message.role"
          >
            <p>{{ message.content }}</p>
          </article>
        </div>
        <form @submit.prevent="ask">
          <label class="sr-only" for="copilot-question">基于当前论文提问</label
          ><textarea
            id="copilot-question"
            v-model="question"
            rows="1"
            maxlength="4000"
            placeholder="基于当前论文提问…"
            :disabled="sending"
          ></textarea
          ><button type="submit" :disabled="sending || !question.trim()">
            {{ sending ? "发送中…" : "➤" }}
          </button>
        </form>
        <p v-if="!isConversationMode" class="disclaimer">
          AI 内容仅供参考，请结合原文理解。
        </p>
      </div>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
    </section>
  </aside>
</template>
<style scoped>
.context {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  height: calc(100vh - 70px);
  box-sizing: border-box;
  padding: 12px;
  background: #f8faff;
  border-left: 1px solid #e5eaf2;
}
.records,
.panel {
  border: 1px solid #e1e7f0;
  border-radius: 8px;
  background: #fff;
}
.assistant-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(145deg, #ffffff 0%, #f8fbff 100%);
}
.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  flex: none;
  min-height: 48px;
  border-bottom: 1px solid #e5eaf2;
}
.tabs button {
  border: 0;
  border-bottom: 2px solid transparent;
  background: #fff;
  color: #344054;
  font: inherit;
  font-weight: 750;
}
.tabs button[aria-selected="true"] {
  border-color: #0868f7;
  color: #0868f7;
}
.tabs button:focus-visible {
  outline: 2px solid #0868f7;
  outline-offset: -3px;
}
.translation-empty {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 42px 28px;
  color: #344054;
  text-align: center;
  line-height: 1.65;
}
.translation-empty span {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
  background: #eaf2ff;
  color: #0868f7;
  font-weight: 800;
}
.translation-empty p {
  margin: 0;
  color: #667085;
  font-size: 12px;
}
.translation-content {
  overflow: auto;
  padding: 18px;
}
.assistant-header {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid #e5eaf2;
}
.assistant-header h2 {
  margin: 0;
  font-size: 17px;
}
.assistant-mark {
  display: grid;
  width: 26px;
  height: 26px;
  place-items: center;
  border-radius: 8px;
  background: #eaf2ff;
  color: #0868f7;
  font-weight: 800;
}
.records {
  padding: 14px 16px;
}
.records header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.records h2 {
  margin: 0;
  font-size: 16px;
}
.records header button {
  border: 0;
  background: transparent;
  color: #0868f7;
  font: inherit;
  font-weight: 700;
}
.counts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
  color: #667085;
  font-size: 11px;
}
.count {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}
.count i {
  display: grid;
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 6px;
  font-style: normal;
  font-size: 13px;
  font-weight: 800;
}
.count em {
  overflow: hidden;
  font-style: normal;
  white-space: nowrap;
}
.count-highlight i {
  background: #fff1d6;
  color: #f59e0b;
}
.count-note i {
  background: #e6efff;
  color: #1769e8;
}
.count-question i {
  background: #f0e7ff;
  color: #7c3aed;
}
.count-bookmark i {
  background: #dcf7ef;
  color: #10a982;
}
.count b {
  color: #111827;
  font-size: 12px;
}
.record-note,
.context-line,
.disclaimer {
  color: #667085;
  font-size: 12px;
}
.copilot {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
  padding: 14px 16px 12px;
}
.copilot--conversation {
  gap: 12px;
  padding-top: 16px;
}
.copilot h3 {
  margin: 2px 0 4px;
  font-size: 13px;
}
.context-line {
  margin: 0;
}
.assistant-actions {
  display: grid;
  gap: 7px;
}
.assistant-actions button {
  display: grid;
  grid-template-columns: 34px 1fr;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 8px 10px;
  border: 1px solid #e5eaf2;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.9);
  color: #182235;
  text-align: left;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.assistant-actions button:hover {
  border-color: #a9c8ff;
  background: #f6f9ff;
}
.assistant-actions button:focus-visible {
  outline: 2px solid #0868f7;
  outline-offset: 2px;
}
.assistant-actions i {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 8px;
  background: #eaf2ff;
  color: #0868f7;
  font-style: normal;
  font-size: 17px;
  font-weight: 800;
}
.assistant-actions button:nth-child(3) i {
  background: #e4faf5;
  color: #00a98f;
}
.assistant-actions button:nth-child(4) i,
.assistant-actions button:nth-child(5) i {
  background: #fff3df;
  color: #ef8b00;
}
.assistant-actions span {
  display: grid;
  gap: 3px;
}
.assistant-actions b {
  font-size: 13px;
}
.assistant-actions small {
  color: #667085;
  font-size: 11px;
  border: 0;
  padding: 0;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.count:focus-visible { outline: 2px solid #0868f7; outline-offset: 3px; border-radius: 6px; }
.messages {
  display: grid;
  align-content: start;
  gap: 8px;
  min-height: 42px;
  max-height: 18vh;
  overflow: auto;
}
.messages--conversation {
  flex: 1;
  max-height: none;
  min-height: 0;
  padding-right: 2px;
}
.messages article {
  padding: 9px;
  border-radius: 7px;
  background: #f4f7fb;
  font-size: 13px;
  line-height: 1.5;
}
.messages article.user {
  background: #e9f1ff;
}
.messages p {
  margin: 0;
}
.copilot form {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  margin-top: auto;
}
.copilot textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid #dce4f0;
  border-radius: 7px;
  min-height: 46px;
  padding: 12px;
  font: inherit;
  resize: none;
}
.copilot form button {
  align-self: end;
  width: 46px;
  min-height: 46px;
  border: 0;
  border-radius: 6px;
  padding: 0 12px;
  background: #0868f7;
  color: #fff;
  font: inherit;
  font-weight: 700;
}
.copilot form button:disabled {
  opacity: 0.5;
}
.disclaimer {
  margin: 0;
  text-align: center;
}
.error {
  margin: 0;
  color: #b42318;
  font-size: 12px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
@media (max-width: 1279px) {
  .context {
    padding-inline: 10px;
  }
}
@media (max-width: 1023px) {
  .context {
    min-width: 0;
    height: auto;
    border-left: 0;
    border-top: 1px solid #e5eaf2;
  }
}
</style>
