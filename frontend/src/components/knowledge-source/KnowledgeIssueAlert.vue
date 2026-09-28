<script setup lang="ts">import type { KnowledgeBaseSummary } from "../../api/knowledgeSources"; defineProps<{ summary: KnowledgeBaseSummary | null }>(); defineEmits<{ view: [] }>();</script>
<template>
  <section
    v-if="summary && summary.needs_attention_count"
    class="alert"
    role="status"
  >
    <b aria-hidden="true">▲</b><div><strong>{{ summary.needs_attention_count }} 个文档需要处理</strong><p>{{ summary.issue_breakdown.parse_failed }} 个解析失败 · {{ summary.issue_breakdown.unsupported_format }} 个格式不支持 · {{ summary.issue_breakdown.unavailable_file }} 个文件无法访问</p></div><button
      type="button"
      @click="$emit('view')"
    >
      查看问题文档　→
    </button>
  </section>
</template>
<style scoped>.alert{display:flex;align-items:center;gap:17px;min-height:77px;margin:16px 0 20px;padding:14px 18px;border:1px solid #ffdfbd;border-radius:12px;background:#fffaf4;color:#13264c}.alert>b{color:#ff6b12;font-size:28px}.alert strong{font-size:18px}.alert p{margin:3px 0 0;color:#5b6b8b;font-size:13px}.alert button{margin-left:auto;min-height:40px;padding:0 20px;border:1px solid #e5eaf5;border-radius:9px;background:#fff;color:#125cff;font-weight:750}@media(max-width:767px){.alert{align-items:flex-start;flex-wrap:wrap}.alert button{width:100%;margin-left:0}}</style>
