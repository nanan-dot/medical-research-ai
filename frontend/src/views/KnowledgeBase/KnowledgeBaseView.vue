Exit code: 0
Wall time: 1.8 seconds
Output:
<script setup lang="ts">
import KnowledgeSourceManager from "../../components/knowledge-source/KnowledgeSourceManager.vue";
</script>

<template>
  <main class="knowledge-page">
    <KnowledgeSourceManager />

    <section
      class="workflow-footer"
      aria-labelledby="after-sync-title"
    >
      <h2 id="after-sync-title">同步后发生什么</h2>
      <div class="workflow-steps">
        <span>识别新增与变更文件</span><b aria-hidden="true">→</b>
        <span>解析支持的文档</span><b aria-hidden="true">→</b>
        <span>建立可用于证据问答的索引</span>
      </div>
      <p>仅扫描你授权的本地目录</p>
    </section>
  </main>
</template>

<style scoped>
.knowledge-page{width:min(100% - 3rem,1280px);margin:0 auto;padding:10px 0 48px}.workflow-footer{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:18px;margin-top:22px;padding:16px 24px;border:1px solid var(--border-subtle);border-radius:12px;background:var(--surface-raised)}.workflow-footer h2{margin:0;color:var(--ink-900,#10213d);font-size:.9rem}.workflow-steps{display:flex;gap:12px;align-items:center;color:var(--text-muted);font-size:.82rem}.workflow-steps b{color:var(--color-primary)}.workflow-footer p{margin:0;color:var(--text-muted);font-size:.78rem;white-space:nowrap}@media(max-width:800px){.knowledge-page{width:min(100% - 2rem,1280px)}.workflow-footer{grid-template-columns:1fr}.workflow-steps{flex-wrap:wrap}.workflow-footer p{white-space:normal}}
</style>
