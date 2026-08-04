<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";
import { knowledgeSourcesApi, type KnowledgeSource } from "../../api/knowledgeSources";

const loading = shallowRef(false);
const error = shallowRef("");
const sources = shallowRef<KnowledgeSource[]>([]);

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    sources.value = await knowledgeSourcesApi.list();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取知识库状态";
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const enabledCount = computed(() => sources.value.filter((source) => source.enabled).length);
const syncingCount = computed(() => sources.value.filter((source) => source.sync_status === "scanning").length);
</script>
<template>
  <section class="knowledge-overview" aria-label="知识库状态">
    <div class="panel-head">
      <h2>知识库状态</h2>
      <RouterLink to="/sources">管理 →</RouterLink>
    </div>
    <p class="source-note">科研资产 · LIVE 状态</p>
    <p v-if="loading" class="hint">正在读取知识源状态…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>
    <template v-else>
      <p v-if="!sources.length" class="hint">尚未登记知识源。前往知识库添加本地文件夹或 Obsidian 库。</p>
      <ul v-else class="asset-list">
        <li v-for="source in sources.slice(0, 4)" :key="source.id" class="asset">
          <span class="asset-icon" aria-hidden="true">◫</span>
          <span class="asset-copy"><b>{{ source.name }}</b><span class="asset-meta">{{ source.enabled ? "已启用" : "未启用" }} · {{ source.sync_status }}</span></span>
          <span class="asset-state" :class="source.enabled ? 'on' : 'off'">{{ source.enabled ? "可用" : "停用" }}</span>
        </li>
      </ul>
      <p v-if="sources.length" class="summary">已启用 {{ enabledCount }} / {{ sources.length }} 个知识源{{ syncingCount ? `，${syncingCount} 个正在同步` : "" }}。论文、笔记与标签随解析与索引持续沉淀。</p>
    </template>
  </section>
</template>
<style scoped>
.knowledge-overview{min-width:0}.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:.4rem}.panel-head h2{margin:0;font-size:1rem;color:var(--text-primary)}.panel-head a{color:var(--text-muted);font-size:.8rem;text-decoration:none}.panel-head a:hover{color:var(--color-primary)}.source-note{margin:0 0 .6rem;color:var(--text-faint);font-size:.72rem}.hint{padding:.85rem .95rem;color:var(--text-muted);font-size:.84rem;background:var(--surface);border:1px dashed var(--border-subtle);border-radius:10px}.hint.error{color:var(--color-danger)}.asset-list{display:grid;gap:2px;margin:0;padding:0;list-style:none}.asset{display:flex;align-items:center;gap:.6rem;min-width:0;padding:.5rem .55rem;border-radius:8px;transition:background-color .15s}.asset:hover{background:var(--surface)}.asset-icon{flex-shrink:0;display:grid;place-items:center;width:26px;height:26px;border-radius:7px;background:var(--surface-muted);color:var(--color-secondary);font-size:.78rem}.asset-copy{display:grid;gap:.1rem;min-width:0}.asset-copy b{font-size:.84rem;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.asset-meta{color:var(--text-faint);font-size:.74rem}.asset-state{flex-shrink:0;font-size:.72rem;font-weight:800}.asset-state.on{color:var(--color-success)}.asset-state.off{color:var(--text-faint)}.summary{margin:.6rem 0 0;color:var(--text-muted);font-size:.8rem;line-height:1.55}
</style>
