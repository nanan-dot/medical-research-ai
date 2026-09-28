<script setup lang="ts">
import type { KnowledgeSource } from "../../api/knowledgeSources";
import { HEALTH_LABEL, SOURCE_TYPE_LABEL, formatDate, formatPercent } from "../../utils/knowledgeSourceFormatter";
import BaseIcon from "../ui/BaseIcon.vue";

defineProps<{ source: KnowledgeSource; actionPending: string | null }>();
defineEmits<{ pin: [KnowledgeSource]; autoSync: [KnowledgeSource, boolean]; sync: [KnowledgeSource]; view: [KnowledgeSource]; menu: [KnowledgeSource] }>();
</script>
<template>
  <article class="row">
    <button
      class="pin"
      type="button"
      :aria-label="source.is_pinned ? `取消置顶 ${source.name}` : `置顶 ${source.name}`"
      :aria-pressed="source.is_pinned"
      @click="$emit('pin',source)"
    >
      <BaseIcon
        name="star"
        :filled="source.is_pinned"
      />
    </button><div class="identity">
      <span
        class="folder"
        aria-hidden="true"
      ><BaseIcon :name="source.source_type === 'obsidian_vault' ? 'document' : 'folder'" /></span><div><strong :title="source.name">{{ source.name }}</strong><em>{{ SOURCE_TYPE_LABEL[source.source_type] }}</em><small :title="source.root_path">{{ source.root_path }}</small></div>
    </div><div class="availability"><span>{{ source.stats.total_files }} {{ source.source_type==='obsidian_vault'?'知识项':'文档' }} · <b>{{ source.stats.available ?? source.stats.indexed }} 已可用</b><i v-if="source.stats.needs_attention ?? source.stats.failed"> · {{ source.stats.needs_attention ?? source.stats.failed }} 需要处理</i></span><small v-if="source.stats.total_files">可用度 {{ formatPercent(source.stats.availability_percent ?? (source.stats.total_files ? (source.stats.available ?? source.stats.indexed) * 100 / source.stats.total_files : null)) }} <u><b :style="{width:`${source.stats.availability_percent ?? 0}%`}" /></u></small><small v-else>暂无同步文档</small></div><div class="sync">
      <time>{{ formatDate(source.last_sync_time) }}</time><label>自动同步 <input
        type="checkbox"
        role="switch"
        :checked="source.auto_sync ?? false"
        :disabled="actionPending===`auto-${source.id}`"
        :aria-label="`${source.name} 自动同步`"
        @change="$emit('autoSync',source,($event.target as HTMLInputElement).checked)"
      ><span /></label><small :class="`health-${source.health_status ?? 'ready'}`">{{ HEALTH_LABEL[source.health_status ?? 'ready'] }}</small>
    </div><div class="actions">
      <button
        type="button"
        :disabled="actionPending===`sync-${source.id}` || source.health_status==='paused'"
        @click="$emit('sync',source)"
      >
        <BaseIcon name="sync" /> {{ actionPending===`sync-${source.id}`?'已提交':'同步' }}
      </button><button
        type="button"
        @click="$emit('view',source)"
      >
        查看{{ source.source_type==='obsidian_vault'?'内容':'文档' }} →
      </button><button
        type="button"
        :aria-label="`${source.name} 更多操作`"
        @click="$emit('menu',source)"
      >
        <BaseIcon name="more" />
      </button>
    </div><p
      v-if="source.error_message"
      class="error"
      role="alert"
    >
      {{ source.error_message }}
    </p>
  </article>
</template>
<style scoped>.row{position:relative;display:grid;grid-template-columns:28px minmax(250px,1.5fr) minmax(220px,1.25fr) 150px auto;gap:16px;align-items:center;min-height:86px;padding:12px 16px;border:1px solid #e3eaf5;border-bottom:0;background:#fff}.row:first-child{border-radius:12px 12px 0 0}.row:last-child{border-bottom:1px solid #e3eaf5;border-radius:0 0 12px 12px}.pin{border:0;background:transparent;color:#adc0e4;font-size:22px}.pin[aria-pressed=true]{color:#ff9b00}.identity{display:flex;align-items:center;gap:12px;min-width:0}.folder{display:grid;width:44px;height:44px;place-items:center;border-radius:10px;background:#eff4ff;color:#1660ff;font-size:24px}.identity div{display:grid;min-width:0;gap:3px}.identity strong,.identity small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.identity strong{color:#16264a}.identity em{justify-self:start;padding:1px 7px;border-radius:7px;background:#edf3ff;color:#155cff;font-size:11px;font-style:normal}.identity small,.availability small,.sync{color:#53678d;font-size:13px}.availability{display:grid;gap:7px}.availability b{color:#18a558}.availability i{color:#f25d20;font-style:normal}.availability u{display:inline-block;width:156px;height:6px;margin-left:8px;border-radius:99px;background:#e6ebf3;text-decoration:none;vertical-align:middle;overflow:hidden}.availability u b{display:block;height:100%;border-radius:inherit;background:#1f66ff}.sync{display:grid;gap:5px}.sync label{display:flex;align-items:center;gap:8px}.sync input{position:absolute;opacity:0}.sync label span{width:34px;height:20px;border-radius:99px;background:#bfc9da}.sync input:checked+span{background:#20aa61}.sync input:focus-visible+span{outline:3px solid #8eb2ff}.health-needs_attention,.health-unavailable{color:#d64f21}.actions{display:flex;gap:8px}.actions button{min-height:40px;padding:0 11px;border:1px solid #dce6f5;border-radius:8px;background:#fff;color:#145dff;font-weight:700;white-space:nowrap}.error{grid-column:2/-1;margin:0;color:#c13d31;font-size:12px}@media(max-width:1279px){.row{grid-template-columns:28px minmax(210px,1.25fr) 1fr auto}.sync{display:none}}@media(max-width:1023px){.row{grid-template-columns:28px 1fr auto}.availability{grid-column:2}.actions{grid-column:3;grid-row:1/3;flex-direction:column}}@media(max-width:767px){.row{grid-template-columns:28px 1fr;padding:14px 12px}.availability{grid-column:2}.sync{display:grid;grid-column:2}.actions{grid-column:1/-1;grid-row:auto;flex-direction:row;flex-wrap:wrap}.actions button{min-height:44px}}</style>
