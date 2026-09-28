<script setup lang="ts">
import { ref } from "vue";
import type { DocumentRecord } from "../../api/documents";
defineProps<{ documents: DocumentRecord[]; disabled: boolean }>();
const selectedIds = defineModel<number[]>({ required: true });
const emit = defineEmits<{ search: [query: string] }>();
const query = ref("");
</script>
<template>
  <fieldset
    id="chat-scope"
    :disabled="disabled"
    tabindex="-1"
  >
    <legend>本次资料范围 <span>{{ selectedIds.length }}/10</span></legend>
    <p>不选资料也可以提问。论文事实需选择对应文献。</p>
    <form
      class="search"
      @submit.prevent="emit('search', query)"
    >
      <label
        class="sr-only"
        for="chat-document-search"
      >搜索资料</label>
      <input
        id="chat-document-search"
        v-model="query"
        type="search"
        placeholder="搜索资料名称"
      >
      <button type="submit">查找</button>
    </form>
    <div class="document-list">
      <label
        v-for="document in documents"
        :key="document.id"
      >
        <input
          v-model="selectedIds"
          type="checkbox"
          :value="document.id"
          :disabled="selectedIds.length >= 10 && !selectedIds.includes(document.id)"
        >
        <span>{{ document.original_filename || '文献 ' + document.id }}<small>{{ document.parse_status === 'succeeded' && document.index_status === 'succeeded' ? '可用于证据检索' : '请检查解析和索引状态' }}</small></span>
      </label>
    </div>
    <p v-if="!documents.length">没有匹配资料。可先进行通用问答，或<a href="/documents">管理资料</a>。</p>
    <button
      v-if="selectedIds.length"
      type="button"
      @click="selectedIds = []"
    >
      清空所选资料
    </button>
    <p class="scope-note">全库检索：尚不可用。本次只检索明确选择的资料。</p>
  </fieldset>
</template>
<style scoped>
fieldset { min-width: 0; border: 0; padding: 0; margin: 0; }
legend { width: 100%; font-size: 15px; font-weight: 650; }
legend span { float: right; color: #526975; font: 12px ui-monospace, monospace; }
p, small { color: #526975; font-size: 12px; line-height: 1.65; }
.search { display: flex; gap: 6px; margin: 16px 0; }
input[type="search"] { min-width: 0; width: 100%; padding: 8px; border: 1px solid #c5d2da; border-radius: 6px; }
button { border: 1px solid #c5d2da; background: white; border-radius: 6px; padding: 7px 10px; white-space: nowrap; cursor: pointer; }
.document-list { max-height: 260px; overflow-y: auto; }
.document-list label { display: flex; align-items: flex-start; gap: 8px; padding: 10px 0; border-bottom: 1px solid #e8eef1; font-size: 13px; overflow-wrap: anywhere; }
.document-list input { margin-top: 3px; accent-color: #237a70; }
small { display: block; margin-top: 4px; }
.scope-note { margin-top: 16px; }
a { color: #225c9a; text-decoration: underline; }
.sr-only { position: absolute; width: 1px; height: 1px; clip-path: inset(50%); overflow: hidden; }
:focus-visible { outline: 3px solid #237a70; outline-offset: 3px; }
</style>
