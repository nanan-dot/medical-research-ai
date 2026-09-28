<script setup lang="ts">
import type { ChatMessage } from "../../types/researchChat";
import { citationLink, sourceLabel, statusLabel, warningLabel } from "./chatLabels";
defineProps<{ message: ChatMessage }>();
</script>
<template>
  <article
    class="chat-message"
    :class="{ 'is-user': message.role === 'user' }"
  >
    <header><strong>{{ sourceLabel(message.source_type) }}</strong><span>{{ statusLabel(message.answer_status) }}</span></header>
    <template v-if="message.sections.length">
      <section
        v-for="(section, index) in message.sections"
        :key="index"
        class="answer-section"
        :data-source="section.source_type"
      >
        <h3>{{ sourceLabel(section.source_type) }}</h3>
        <p class="answer-text">{{ section.content }}</p>
        <details
          v-for="(citation, citationIndex) in section.citations"
          :key="citationIndex"
        >
          <summary>{{ citation.citation_text || (citation.document_id ? '文献 ' + citation.document_id : '来源') }}<span v-if="citation.page"> · 第 {{ citation.page }} 页</span></summary>
          <p v-if="citation.section">{{ citation.section }}</p>
          <blockquote v-if="citation.evidence_text">{{ citation.evidence_text }}</blockquote>
          <p>{{ citation.source_level === 'abstract' ? '来源层级：摘要' : citation.source_level === 'metadata' ? '来源层级：题录' : '来源层级：文献摘录' }}</p>
          <a
            v-if="citationLink(citation)"
            :href="citationLink(citation)!"
            target="_blank"
            rel="noopener noreferrer"
          >{{ citation.document_id ? '打开资料详情核对原文' : '打开 PubMed 记录' }}</a>
        </details>
      </section>
    </template>
    <template v-else>
      <p class="answer-text">{{ message.content }}</p>
      <details
        v-for="(citation, index) in message.citations"
        :key="index"
      >
        <summary>{{ citation.citation_text || '历史引用' }}</summary>
        <blockquote>{{ citation.evidence_text }}</blockquote>
        <a
          v-if="citationLink(citation)"
          :href="citationLink(citation)!"
          target="_blank"
          rel="noopener noreferrer"
        >打开来源</a>
      </details>
    </template>
    <ul
      v-if="message.warnings.length"
      class="warnings"
    >
      <li
        v-for="code in message.warnings"
        :key="code"
      >
        {{ warningLabel(code) }}
      </li>
    </ul>
  </article>
</template>
<style scoped>
.chat-message { border: 1px solid #dce4e8; border-radius: 12px; padding: 20px; background: #fff; }
.chat-message.is-user { margin-left: 8%; background: #f1f6f9; border-color: transparent; }
header { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; color: #264653; font-size: 13px; }
header span { color: #526975; }
.answer-section { margin-top: 16px; padding-left: 14px; border-left: 3px solid #93a7b3; }
.answer-section[data-source="paper_grounded"] { border-left-color: #237a70; }
.answer-section[data-source="web_augmented"] { border-left-color: #6664a6; }
h3 { font-size: 12px; color: #536775; margin: 0 0 8px; }
.answer-text, blockquote { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.85; font-size: 14px; }
.answer-text { margin: 8px 0; }
details { margin-top: 12px; font-size: 12px; }
summary { cursor: pointer; overflow-wrap: anywhere; }
blockquote { margin: 10px 0; padding: 10px; background: #f5f8fa; }
a { color: #225c9a; text-decoration: underline; }
.warnings { color: #7a5518; font-size: 12px; padding-left: 18px; }
:focus-visible { outline: 3px solid #237a70; outline-offset: 3px; }
</style>
