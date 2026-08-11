<script setup lang="ts">
import KnowledgeSourceManager from "../../components/knowledge-source/KnowledgeSourceManager.vue";
</script>

<template>
  <main class="knowledge-page">
    <section class="workflow-strip" aria-label="知识库工作流程"><span><b>1</b> 知识来源</span><i>→</i><span><b>2</b> 同步目录</span><i>→</i><span><b>3</b> 文档解析与索引</span><em>仅扫描你授权的本地目录</em></section>
    <KnowledgeSourceManager />
    <section class="workflow-footer" aria-labelledby="after-sync"><h2 id="after-sync">同步后发生什么</h2><div><span>识别新增与变更文件</span><b>→</b><span>解析支持的文档</span><b>→</b><span>建立可用于证据问答的索引</span></div></section>
  </main>
</template>

<style scoped>
.knowledge-page { width: min(100% - 3rem, 1440px); margin: 0 auto; padding: 1rem 0 2.75rem; display:grid; gap:1rem; }
.workflow-strip,.workflow-footer { border:1px solid var(--border-subtle); border-radius:12px; background:var(--surface-raised); }
.workflow-strip { min-height:68px; display:flex; align-items:center; gap:2rem; padding:1rem 1.5rem; color:#526786; }.workflow-strip span { white-space:nowrap; font-weight:700; }.workflow-strip b { display:inline-grid; place-items:center; width:22px; height:22px; margin-right:.55rem; border-radius:50%; background:var(--color-primary); color:#fff; font-size:.78rem; }.workflow-strip i { color:#64748b; font-size:1.5rem; font-style:normal; }.workflow-strip em { margin-left:auto; color:var(--text-muted); font-size:.85rem; font-style:normal; }
.workflow-footer { padding:1.2rem 1.5rem; background:#f8fbff; }.workflow-footer h2 { margin:0 0 .75rem; font-size:1.15rem; }.workflow-footer div { display:flex; align-items:center; justify-content:space-between; gap:1rem; color:#526786; }.workflow-footer b { color:var(--color-primary); }
@media(max-width:768px){.workflow-strip,.workflow-footer div{align-items:flex-start;flex-direction:column;gap:.55rem}.workflow-strip em{margin-left:0}.workflow-strip i{display:none}}
</style>
