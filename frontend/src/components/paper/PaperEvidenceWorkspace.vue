<script setup lang="ts">
import { computed, shallowRef, watch } from "vue";

import type { Citation } from "../../api/conversations";
import type { DocumentRecord } from "../../api/documents";
import { usePaperEvidenceWorkspace } from "../../composables/usePaperEvidenceWorkspace";

const props = defineProps<{ document: DocumentRecord | null; canCreate: boolean }>();
const emit = defineEmits<{ changePaper: []; returnOverview: [] }>();
const documentRef = computed(() => props.document);
const canCreateRef = computed(() => props.canCreate);
const workspace = usePaperEvidenceWorkspace(documentRef, canCreateRef);
const question = shallowRef("");
const selectedCitation = shallowRef<Citation | null>(null);

const documentTitle = computed(() => props.document?.original_filename || props.document?.file_path || "未提供");
const documentStatus = computed(() => {
  if (!props.document) return "未选择论文";
  return `解析：${props.document.parse_status} · 索引：${props.document.index_status}`;
});
const citations = computed(() => workspace.latestAssistant.value?.citations ?? []);
const latestQuestion = computed(() => workspace.conversation.value?.messages.filter((message) => message.role === "user").at(-1)?.content ?? null);
const answerStatus = computed(() => workspace.latestAssistant.value?.answer_status);
const answerLabel = computed(() => {
  if (answerStatus.value === "insufficient_evidence") return "证据不足 / 需人工核对";
  if (citations.value.length === 0) return "无可定位来源";
  if (answerStatus.value === "answered") return `已关联 ${citations.value.length} 个来源`;
  return "需要回源核对的证据摘要";
});

async function submit(): Promise<void> {
  const value = question.value;
  if (await workspace.ask(value)) question.value = "";
}
function selectCitation(citation: Citation): void { selectedCitation.value = citation; }

watch(() => props.document?.id, () => {
  // 引用属于某次回答；切换论文后必须先清空，不能让旧论文的来源残留在当前工作台。
  selectedCitation.value = null;
});
</script>

<template>
  <section class="evidence-workspace" aria-label="当前论文证据问答工作台">
    <header class="paper-context">
      <div><p class="context-label">当前论文</p><strong class="paper-title">{{ documentTitle }}</strong><p class="document-status">{{ documentStatus }}</p></div>
      <div class="context-actions"><button type="button" @click="emit('changePaper')">更换论文</button><button type="button" @click="emit('returnOverview')">返回研究概览</button></div>
    </header>
    <p v-if="!props.document" class="empty-context" role="status">请先在研究概览选择一篇已索引论文，再开始证据问答。</p>
    <div v-else class="workspace-grid">
      <aside class="scope-panel"><p class="eyebrow">CURRENT PAPER</p><h2>当前论文范围</h2><p>本次问答仅围绕当前论文，不会混入其他文献。</p><p v-if="workspace.loading.value" role="status">正在读取关联会话…</p><p v-else-if="workspace.error.value" role="alert" class="error">{{ workspace.error.value }}</p><template v-else><div class="history-heading"><strong>问题历史</strong><span>{{ workspace.documentHistory.value.length ? "当前论文关联会话" : "尚无关联会话" }}</span></div><button v-for="item in workspace.documentHistory.value" :key="item.id" type="button" class="history-item" :class="{ active: workspace.conversation.value?.id === item.id }" :aria-current="workspace.conversation.value?.id === item.id ? 'true' : undefined" @click="workspace.openConversation(item.id)"><strong>{{ item.title || "未提供" }}</strong><span>真实消息 {{ item.message_count }} 条</span></button><div v-if="!workspace.conversation.value" class="no-conversation"><p>尚无与当前论文关联的问答会话。</p><button type="button" :disabled="!props.canCreate || workspace.creating.value" @click="workspace.createConversation">{{ workspace.creating.value ? "创建中…" : "创建问答会话" }}</button><p v-if="!props.canCreate">当前文档尚未完成解析和索引，暂不能创建问答会话。</p></div></template></aside>
      <section class="answer-panel" aria-labelledby="answer-title"><header><p class="eyebrow">EVIDENCE SUMMARY</p><h2 id="answer-title">待核对的论文式回答</h2></header><p v-if="workspace.error.value && !workspace.loading.value" class="error" role="alert">{{ workspace.error.value }}</p><template v-else-if="workspace.latestAssistant.value"><article class="answer"><div class="answer-status" :class="{ warning: answerStatus === 'insufficient_evidence' }">{{ answerLabel }}</div><p v-if="answerStatus === 'insufficient_evidence'" class="warning-copy">证据不足时，系统不能把推断当作论文事实；请结合原文来源人工核对。</p><p v-if="workspace.latestAssistant.value.uncertainty !== undefined" class="metadata">不确定性：{{ workspace.latestAssistant.value.uncertainty }}</p><p v-if="workspace.latestAssistant.value.reason_codes?.length" class="metadata">原因代码：{{ workspace.latestAssistant.value.reason_codes.join("、") }}</p><div class="answer-content">{{ workspace.latestAssistant.value.content }}</div><div class="answer-actions"><button type="button" :disabled="citations.length === 0" @click="citations[0] && selectCitation(citations[0])">打开所选来源</button><button type="button" @click="workspace.feedback(workspace.latestAssistant.value!, 1)">回答有帮助</button><button type="button" @click="workspace.feedback(workspace.latestAssistant.value!, -1)">引用/数据需修正</button></div></article></template><p v-else class="answer-empty" role="status">创建或打开会话后，在此查看需要回源核对的回答与引用。</p><form class="question-form" @submit.prevent="submit"><label for="paper-evidence-question">基于当前论文提问</label><p>问题只会发送到当前论文关联的问答会话。</p><textarea id="paper-evidence-question" v-model="question" :disabled="!workspace.conversation.value || workspace.asking.value" required maxlength="4000" placeholder="询问研究方法、结果或结论的原文依据"></textarea><button type="submit" :disabled="!workspace.conversation.value || workspace.asking.value || !question.trim()">{{ workspace.asking.value ? "问答中…" : "发送问题" }}</button></form></section>
      <aside class="citation-panel"><p class="eyebrow">TRACEABILITY</p><h2>来源与可追溯性</h2><p v-if="citations.length === 0" class="empty-citations">当前回答没有可定位来源。</p><button v-for="citation in citations" :key="citation.id" type="button" class="citation-card" :class="{ selected: selectedCitation?.id === citation.id }" @click="selectCitation(citation)"><strong>{{ citation.citation_text || "未提供" }}</strong><span>章节：{{ citation.section || "未提供" }}</span><span>页码：{{ citation.page ?? "未提供" }}</span><small>{{ citation.evidence_text || "未提供" }}</small></button><article v-if="selectedCitation" class="selected-source"><h3>已选来源</h3><p>检索/证据状态：当前回答返回的引用</p><p>章节：{{ selectedCitation.section || "未提供" }} · 页码：{{ selectedCitation.page ?? "未提供" }}</p><blockquote>{{ selectedCitation.evidence_text || "未提供" }}</blockquote><p class="unavailable">原文定位：UNAVAILABLE（当前工作台没有可复用的真实定位接口）。</p></article></aside>
    </div>
    <p v-if="latestQuestion" class="latest-question">当前问题：{{ latestQuestion }}</p>
  </section>
</template>

<style scoped>
.evidence-workspace{display:grid;gap:1rem;min-height:calc(100vh - 180px)}.paper-context{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.8rem 1rem;border:1px solid var(--border-subtle);background:var(--surface)}.context-label,.document-status,.metadata,.scope-panel p,.empty-citations,.unavailable{margin:0;color:var(--text-muted);font-size:.8rem}.paper-title{display:block;max-width:62rem;margin:.12rem 0;overflow-wrap:anywhere;color:var(--text-primary);font-size:1rem}.context-actions,.answer-actions{display:flex;flex-wrap:wrap;gap:.5rem}.context-actions button,.answer-actions button,.question-form button,.no-conversation button{border:1px solid var(--border-strong);border-radius:6px;padding:.5rem .65rem;background:var(--surface);color:var(--text-primary);font:inherit;cursor:pointer}.context-actions button:first-child,.question-form button,.no-conversation button{border-color:var(--color-primary);background:var(--color-primary);color:var(--on-primary)}.workspace-grid{display:grid;grid-template-columns:minmax(210px,21fr) minmax(0,54fr) minmax(230px,25fr);min-height:0;border:1px solid var(--border-subtle);background:var(--surface)}.scope-panel,.citation-panel{display:grid;align-content:start;gap:.75rem;padding:1rem;background:var(--surface-raised)}.scope-panel{border-right:1px solid var(--border-subtle)}.citation-panel{border-left:1px solid var(--border-subtle)}.scope-panel h2,.answer-panel h2,.citation-panel h2{margin:0;color:var(--text-primary);font-size:1.2rem}.eyebrow{margin:0;color:var(--color-primary);font-size:.7rem;font-weight:800;letter-spacing:.09em}.history-heading{display:grid;gap:.18rem;padding-top:.8rem;border-top:1px solid var(--border-subtle);font-size:.82rem}.history-heading span,.history-item span{color:var(--text-muted);font-size:.75rem}.history-item,.citation-card{display:grid;gap:.28rem;width:100%;padding:.65rem;border:1px solid var(--border-subtle);border-radius:6px;background:var(--surface);color:var(--text-primary);text-align:left;cursor:pointer}.history-item.active,.citation-card.selected{border-left:3px solid var(--color-primary);background:var(--color-primary-soft)}.history-item strong,.citation-card strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.no-conversation{display:grid;gap:.55rem;padding-top:.8rem;border-top:1px solid var(--border-subtle);font-size:.84rem}.no-conversation p{margin:0}.answer-panel{display:grid;align-content:start;gap:1rem;min-width:0;padding:1.25rem;background:var(--page-bg)}.answer{display:grid;gap:.8rem;padding:1rem;border-left:3px solid var(--color-primary);background:var(--surface)}.answer-status{width:max-content;max-width:100%;padding:.25rem .45rem;background:var(--color-primary-soft);color:var(--color-primary);font-size:.78rem;font-weight:700}.answer-status.warning{background:var(--color-warning-soft);color:var(--color-warning)}.warning-copy{margin:0;color:var(--text-primary);font-size:.88rem}.answer-content{white-space:pre-wrap;color:var(--text-primary);font-size:.94rem;line-height:1.7}.answer-empty,.empty-context{padding:1rem;border:1px dashed var(--border-strong);color:var(--text-muted)}.question-form{display:grid;gap:.5rem;padding-top:1rem;border-top:1px solid var(--border-subtle)}.question-form label{color:var(--text-primary);font-size:1rem;font-weight:700}.question-form p{margin:0;color:var(--text-muted);font-size:.8rem}.question-form textarea{min-height:6rem;resize:vertical;padding:.65rem;border:1px solid var(--border-strong);border-radius:6px;background:var(--surface);color:var(--text-primary);font:inherit}.question-form button{justify-self:start}.question-form button:disabled,.no-conversation button:disabled,.answer-actions button:disabled{opacity:.55;cursor:not-allowed}.citation-card span,.citation-card small{color:var(--text-muted);font-size:.78rem}.citation-card small{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:3}.selected-source{display:grid;gap:.45rem;padding-top:.85rem;border-top:1px solid var(--border-subtle);font-size:.82rem}.selected-source h3,.selected-source p{margin:0}.selected-source blockquote{margin:0;padding-left:.65rem;border-left:2px solid var(--color-primary);color:var(--text-muted)}.error{margin:0;color:var(--color-danger)}@media(max-width:1279px){.workspace-grid{grid-template-columns:minmax(210px,28%) minmax(0,72%)}.citation-panel{grid-column:1/-1;border-top:1px solid var(--border-subtle);border-left:0}.citation-card{max-width:36rem}}@media(max-width:1023px){.workspace-grid{grid-template-columns:1fr}.scope-panel,.citation-panel{border:0;border-bottom:1px solid var(--border-subtle)}.citation-panel{order:3}.paper-context{align-items:flex-start;flex-direction:column}}@media(prefers-reduced-motion:reduce){.history-item,.citation-card{transition:none}}
</style>
