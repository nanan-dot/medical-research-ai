<script setup lang="ts">
import type { DocumentRecord } from "../../api/documents";

const props = defineProps<{ document: DocumentRecord | null; canAnnotate: boolean }>();
const emit = defineEmits<{ open: [] }>();
</script>

<template>
  <section class="annotation-section" aria-labelledby="annotation-title">
    <header class="section-header"><p class="eyebrow">READING ANNOTATIONS</p><h2 id="annotation-title" class="section-title">阅读与批注</h2><p class="section-description">在 PDF 阅读区查看原文并管理该论文的批注。</p></header>
    <p v-if="!props.document" class="state-copy">请先选择当前论文，再进入原文阅读和批注。</p>
    <template v-else-if="props.canAnnotate"><p class="state-copy">将打开当前论文的既有 PDF 阅读与批注工作区；批注继续绑定该文档版本。</p><button class="primary-action" type="button" @click="emit('open')">打开阅读批注</button></template>
    <p v-else class="unavailable">当前文档不是可预览的 PDF，无法进入 PDF 批注区。</p>
  </section>
</template>

<style scoped>
.annotation-section { display: grid; gap: .72rem; padding: 1.15rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); background: var(--surface); box-shadow: var(--shadow); }.section-header { display: grid; gap: .3rem; }.eyebrow { margin: 0; color: var(--color-primary); font-size: .7rem; font-weight: 900; letter-spacing: .1em; }.section-title { margin: 0; color: var(--text-primary); font-size: 1.18rem; }.section-description,.state-copy,.unavailable { margin: 0; color: var(--text-muted); font-size: .86rem; }.primary-action { justify-self: start; padding: .62rem .85rem; border: 1px solid var(--color-primary); border-radius: 8px; background: var(--color-primary); color: #fff; font: inherit; font-weight: 750; }
</style>
