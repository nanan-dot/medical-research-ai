<script setup lang="ts">
import type { Conversation } from "../../api/conversations";
import type { DocumentRecord } from "../../api/documents";

const props = defineProps<{
  document: DocumentRecord | null;
  conversation: Conversation | null;
  loading: boolean;
  error: string | null;
  canStart: boolean;
}>();

const emit = defineEmits<{ create: []; open: [conversationId: number] }>();
</script>

<template>
  <section class="conversation-section" aria-labelledby="single-paper-chat-title">
    <header class="section-header"><p class="eyebrow">SINGLE-PAPER CHAT</p><h2 id="single-paper-chat-title" class="section-title">单篇证据问答</h2><p class="section-description">围绕当前论文进行可恢复的证据问答，不混入多篇研究上下文。</p></header>
    <p v-if="!props.document" class="state-copy">请先选择当前论文，再读取该论文的问答会话。</p>
    <template v-else>
      <p class="scope">证据范围：仅当前论文《{{ props.document.original_filename || props.document.file_path }}》</p>
      <p v-if="props.error" class="error" role="alert">{{ props.error }}</p>
      <p v-else-if="props.loading" class="state-copy">正在读取最近单篇问答会话…</p>
      <template v-else-if="props.conversation"><p class="state-copy">已找到最近会话，包含 {{ props.conversation.messages.length }} 条消息。</p><button class="primary-action" type="button" @click="emit('open', props.conversation.id)">继续最近会话</button></template>
      <template v-else><p class="state-copy">尚无该论文的单篇问答会话。新建后只会绑定当前这一篇论文。</p><button class="primary-action" type="button" :disabled="!props.canStart" @click="emit('create')">新建单篇问答</button><p v-if="!props.canStart" class="unavailable">当前文档尚未完成解析和索引，暂不能创建问答。</p></template>
    </template>
  </section>
</template>

<style scoped>
.conversation-section { display: grid; gap: .72rem; padding: 1.15rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); background: var(--surface); box-shadow: var(--shadow); }.section-header { display: grid; gap: .3rem; }.eyebrow { margin: 0; color: var(--color-primary); font-size: .7rem; font-weight: 900; letter-spacing: .1em; }.section-title { margin: 0; color: var(--text-primary); font-size: 1.18rem; }.section-description,.state-copy,.unavailable { margin: 0; color: var(--text-muted); font-size: .86rem; }.scope { margin: 0; padding: .62rem .7rem; border-radius: 8px; background: var(--surface-muted); color: var(--text-primary); font-size: .84rem; }.primary-action { justify-self: start; padding: .62rem .85rem; border: 1px solid var(--color-primary); border-radius: 8px; background: var(--color-primary); color: #fff; font: inherit; font-weight: 750; }.primary-action:disabled { opacity: .55; cursor: not-allowed; }.error { margin: 0; color: var(--color-danger); }
</style>
