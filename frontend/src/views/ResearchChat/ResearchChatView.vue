<script setup lang="ts">
import { onMounted } from "vue";
import ChatMessage from "../../components/ResearchChat/ChatMessage.vue";
import ChatScope from "../../components/ResearchChat/ChatScope.vue";
import { useResearchChat } from "../../composables/useResearchChat";

const { capabilities, conversation, summaries, documents, gaps, selectedIds, question, mode,
  allowSupplement, allowWeb, webQuery, isBusy, isLoading, error, notice, lastAnswer, pending, canSend,
  initialize, searchDocuments, load, newConversation, send, recover, cancel, deleteGap } = useResearchChat();
function focusElement(id: string): void { document.getElementById(id)?.focus(); }
function selectConversation(event: Event): void { void load(Number((event.target as HTMLSelectElement).value)); }
function act(action: string): void {
  if (action === "select_documents") focusElement("chat-scope");
  else if (action === "select_mode") focusElement("chat-mode");
  else if (action === "enable_web" || action === "edit_web_query") { allowWeb.value = true; setTimeout(() => focusElement("chat-web-query"), 0); }
  else if (action === "retry") { focusElement("chat-question"); }
}
const actionLabels: Record<string, string> = { select_documents: "调整资料范围", select_mode: "调整回答模式", enable_web: "设置外部检索", edit_web_query: "修改检索词", retry: "编辑并重新发送" };
onMounted(initialize);
</script>
<template>
  <div class="research-chat">
    <header class="page-heading">
      <div><p class="eyebrow">研究工作区 / 对话</p><h1>统一科研对话</h1><p>从一个问题开始，让每一段回答都有清楚的来源。</p></div>
      <button
        type="button"
        :disabled="isBusy || isLoading"
        @click="newConversation"
      >
        新建对话
      </button>
    </header>
    <p
      v-if="isLoading"
      role="status"
    >
      正在加载对话工作区…
    </p>
    <div
      v-if="capabilities && !capabilities.migration_ready"
      class="alert"
      role="alert"
    >
      <h2>对话数据尚未升级</h2><p>请由管理员备份数据库并执行已提供的升级脚本，然后重新加载。本页面不会自动改动现有数据库。</p>
      <button
        type="button"
        @click="initialize"
      >
        重新检查
      </button>
    </div>
    <p
      v-if="error"
      class="alert"
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-if="notice"
      class="notice"
      role="status"
    >
      {{ notice }}
    </p>
    <div class="workspace">
      <section
        class="conversation-column"
        aria-label="科研对话"
      >
        <div class="conversation-toolbar">
          <label for="chat-history">历史对话</label>
          <select
            id="chat-history"
            :value="conversation?.id ?? ''"
            :disabled="isBusy || isLoading"
            @change="selectConversation"
          >
            <option value="">选择已保存对话</option>
            <option
              v-for="summary in summaries"
              :key="summary.id"
              :value="summary.id"
            >
              {{ summary.title || '对话 ' + summary.id }}
            </option>
          </select>
        </div>
        <div
          class="messages"
          :aria-busy="isBusy"
        >
          <div
            v-if="!conversation?.messages.length"
            class="empty-state"
          >
            <span
              class="empty-mark"
              aria-hidden="true"
            >?</span><h2>研究问题，不必从上传开始</h2>
            <p>概念、方法和写作可以直接讨论。询问具体论文时，再选择右侧资料。</p>
            <div class="examples">
              <button
                type="button"
                @click="question = '什么是系统综述？'; focusElement('chat-question')"
              >
                什么是系统综述？
              </button><button
                type="button"
                @click="question = '这篇论文的主要结论是什么？'; focusElement('chat-scope')"
              >
                讨论一篇论文
              </button>
            </div>
          </div>
          <ChatMessage
            v-for="message in conversation?.messages ?? []"
            :key="message.id"
            :message="message"
          />
        </div>
        <p
          v-if="isBusy"
          class="progress"
          role="status"
        >
          正在回答… 完成后显示完整答案。
        </p>
        <div
          v-if="lastAnswer?.suggested_actions.length"
          class="actions"
          aria-label="后续操作"
        >
          <template
            v-for="action in lastAnswer.suggested_actions"
            :key="action"
          >
            <a
              v-if="action === 'configure_model'"
              href="/models"
            >检查模型设置</a>
            <a
              v-else-if="action === 'open_documents'"
              href="/documents"
            >管理资料</a>
            <button
              v-else-if="actionLabels[action]"
              type="button"
              :disabled="isBusy"
              @click="act(action)"
            >
              {{ actionLabels[action] }}
            </button>
          </template>
        </div>
        <div
          v-if="pending && !isBusy"
          class="notice"
        >
          请求结果尚未确认。
          <button
            type="button"
            @click="recover"
          >
            恢复请求结果
          </button>
          <button
            type="button"
            @click="cancel"
          >
            取消未完成请求
          </button>
        </div>
        <form
          class="composer"
          @submit.prevent="send"
        >
          <div class="mode-row">
            <label for="chat-mode">回答模式</label><select
              id="chat-mode"
              v-model="mode"
              :disabled="isBusy"
            >
              <option value="auto">自动分流</option><option value="general">通用回答</option><option value="evidence_only">仅文献证据</option>
            </select>
          </div>
          <label for="chat-question">你的问题</label>
          <textarea
            id="chat-question"
            v-model="question"
            rows="4"
            maxlength="4000"
            placeholder="输入研究问题…"
            :disabled="isBusy || isLoading"
            @keydown.ctrl.enter.prevent="send"
            @keydown.meta.enter.prevent="send"
          />
          <div class="options">
            <label><input
              v-model="allowSupplement"
              type="checkbox"
              :disabled="isBusy || mode === 'evidence_only'"
            >证据不足时补充通用解释</label>
            <label><input
              v-model="allowWeb"
              type="checkbox"
              :disabled="isBusy || mode === 'evidence_only'"
            >允许 PubMed 外部检索</label>
          </div>
          <div
            v-if="allowWeb"
            class="web-control"
          >
            <label for="chat-web-query">发送给 PubMed 的公开检索词</label><input
              id="chat-web-query"
              v-model="webQuery"
              maxlength="500"
              :disabled="isBusy"
              placeholder="请勿包含患者信息或未公开研究内容"
            >
            <p>只发送这段检索词；返回题录或摘要。启用后，请在问题中明确要求外部检索。</p>
          </div>
          <footer>
            <span>Ctrl / ⌘ + Enter 发送 · {{ question.length }}/4000</span><button
              v-if="isBusy"
              type="button"
              @click="cancel"
            >
              取消回答
            </button><button
              v-else
              type="submit"
              class="primary"
              :disabled="!canSend"
            >
              发送问题
            </button>
          </footer>
        </form>
      </section>
      <aside
        class="context-column"
        aria-label="资料与知识缺口"
      >
        <ChatScope
          v-model="selectedIds"
          :documents="documents"
          :disabled="isBusy"
          @search="searchDocuments"
        />
        <section class="gaps">
          <h2>知识缺口 <span>{{ gaps.length }}</span></h2><p>只记录所选文献中实际未获充分支持的问题。</p>
          <p v-if="!gaps.length">暂无记录</p>
          <article
            v-for="gap in gaps"
            :key="gap.id"
          >
            <h3>{{ gap.question }}</h3><p>资料 {{ gap.document_ids.join('、') }} · 出现 {{ gap.occurrences }} 次</p>
            <button
              type="button"
              :disabled="isBusy"
              @click="selectedIds = [...gap.document_ids]; question = gap.question; focusElement('chat-scope')"
            >
              补充资料后再问
            </button>
            <button
              type="button"
              :aria-label="'删除知识缺口：' + gap.question"
              @click="deleteGap(gap.id)"
            >
              删除
            </button>
          </article>
        </section>
        <p class="boundary">模型回答用于科研辅助。文献结论请核对原文，医学决策需专业判断。</p>
      </aside>
    </div>
  </div>
</template>
<style scoped>
.research-chat { --ink: #213d4b; --muted: #526975; --line: #dce4e8; --accent: #237a70; --paper: #fff; --wash: #f1f6f9; color: var(--ink); max-width: 1440px; margin: auto; padding: 28px; }
.page-heading { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 28px; }
.eyebrow { font-size: 11px; letter-spacing: .14em; color: var(--muted); margin: 0 0 8px; }
h1 { font-family: "Microsoft YaHei", sans-serif; font-size: 26px; letter-spacing: -.04em; margin: 0; font-weight: 650; }
.page-heading p:last-child { color: var(--muted); font-size: 13px; margin-bottom: 0; }
.workspace { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 28px; }
.conversation-column { min-width: 0; }
.conversation-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; font-size: 12px; }
.conversation-toolbar select { flex: 1; min-width: 0; max-width: 360px; }
.messages { display: grid; gap: 18px; }
.empty-state { text-align: center; padding: 52px 28px; background: var(--paper); border: 1px solid var(--line); border-radius: 12px; }
.empty-mark { display: inline-grid; place-items: center; width: 42px; height: 42px; color: var(--accent); background: #edf6f3; border-radius: 50%; font: 28px Georgia, serif; }
.empty-state h2 { font-size: 20px; margin-top: 18px; }
.empty-state p { color: var(--muted); font-size: 13px; line-height: 1.9; }
.examples, .actions { display: flex; justify-content: center; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
.composer { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 18px; margin-top: 22px; }
.mode-row { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
label { font-size: 12px; }
textarea { display: block; width: 100%; resize: vertical; min-height: 100px; box-sizing: border-box; margin: 8px 0 12px; font: inherit; font-size: 14px; line-height: 1.7; padding: 12px; }
button, select, textarea, input:not([type="checkbox"]) { border: 1px solid #c5d2da; border-radius: 6px; background: white; color: var(--ink); }
button, select { padding: 8px 12px; font-size: 12px; }
button { cursor: pointer; }
button:disabled { opacity: .5; cursor: not-allowed; }
.primary { background: var(--accent); color: white; border-color: var(--accent); padding: 10px 20px; }
.options { display: flex; flex-wrap: wrap; gap: 12px; }
.options label { display: flex; align-items: center; gap: 5px; color: var(--muted); }
input[type="checkbox"] { accent-color: var(--accent); }
.web-control { margin-top: 16px; }
.web-control input { display: block; width: 100%; box-sizing: border-box; padding: 10px; margin-top: 8px; font-size: 12px; }
.web-control p, footer span { font-size: 11px; color: var(--muted); line-height: 1.6; }
footer { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-top: 16px; }
.context-column { border-left: 1px solid var(--line); padding-left: 24px; min-width: 0; }
.gaps { margin-top: 28px; padding-top: 24px; border-top: 1px solid var(--line); }
.gaps h2 { font-size: 15px; display: flex; justify-content: space-between; }
.gaps p, .boundary { color: var(--muted); font-size: 12px; line-height: 1.7; }
.gaps article { padding: 12px 0; border-bottom: 1px solid var(--line); }
.gaps h3 { font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.gaps button { padding: 6px; margin-right: 6px; }
.boundary { margin-top: 28px; }
.alert { background: #fff6e9; border: 1px solid #e5c795; color: #72531f; padding: 14px; border-radius: 8px; font-size: 13px; }
.alert h2 { font-size: 16px; }
.notice, .progress { background: var(--wash); font-size: 12px; padding: 12px; line-height: 1.7; }
a { color: #225c9a; text-decoration: underline; font-size: 12px; }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
@media (max-width: 1000px) { .workspace { grid-template-columns: minmax(0, 1fr); } .context-column { border-left: 0; border-top: 1px solid var(--line); padding: 24px 0 0; } }
@media (max-width: 600px) { .research-chat { padding: 16px 10px; } .page-heading { align-items: flex-start; gap: 12px; } h1 { font-size: 22px; } .page-heading button { white-space: nowrap; } .empty-state { padding: 28px 16px; } footer { flex-wrap: wrap; } }
</style>
