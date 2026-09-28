<script setup lang="ts">
import type { KnowledgeBaseSummary } from "../../api/knowledgeSources";
import { formatPercent } from "../../utils/knowledgeSourceFormatter";
import BaseIcon from "../ui/BaseIcon.vue";

defineProps<{ summary: KnowledgeBaseSummary | null; loading: boolean }>();
</script>
<template>
  <section
    class="summary"
    aria-label="知识库汇总"
  >
    <template v-if="summary"><div class="readiness"><span>知识可用度</span><strong>{{ formatPercent(summary.availability_percent) }}</strong><i><b :style="{ width: `${summary.availability_percent ?? 0}%` }" /></i><small>本地 {{ summary.local_folder_count }} · Obsidian {{ summary.obsidian_count }}</small></div><div><b><BaseIcon name="folder" /> {{ summary.source_count }}</b><span>知识来源</span></div><div><b><BaseIcon name="document" /> {{ summary.total_item_count }}</b><span>文档总数</span></div><div><b class="ok"><BaseIcon name="document" /> {{ summary.available_item_count }}</b><span>已可用</span></div><div><b class="warn"><BaseIcon name="alert" /> {{ summary.needs_attention_count }}</b><span>需要处理</span></div></template><span
      v-else
      class="loading"
    >{{ loading ? "正在汇总知识库…" : "汇总暂不可用" }}</span>
  </section>
</template>
<style scoped>.summary{display:grid;grid-template-columns:1.15fr repeat(4,1fr);min-height:142px;border:1px solid #e5eaf5;border-radius:13px;background:#fff;box-shadow:0 7px 20px rgb(45 78 150 / 6%)}.summary>div{display:grid;align-content:center;gap:8px;min-width:0;padding:22px 26px;border-left:1px solid #edf0f7}.summary>div:first-child{border-left:0}.summary span,.summary small{color:#52668c;font-size:13px}.summary b{display:flex;align-items:center;gap:6px;color:#15274d;font-size:24px}.summary b .icon{font-size:21px}.summary .ok{color:#17a45b}.summary .warn{color:#f56b17}.readiness strong{color:#20aa61;font-size:36px;line-height:1}.readiness i{height:9px;border-radius:99px;background:#e7ebf3;overflow:hidden}.readiness i b{display:block;height:100%;border-radius:inherit;background:#21ad63}.loading{align-self:center;padding:24px;color:#65789c}@media(max-width:1279px){.summary{grid-template-columns:repeat(3,1fr)}.readiness{grid-column:span 3}}@media(max-width:767px){.summary{grid-template-columns:repeat(2,1fr)}.readiness{grid-column:span 2}.summary>div{padding:16px}}</style>
