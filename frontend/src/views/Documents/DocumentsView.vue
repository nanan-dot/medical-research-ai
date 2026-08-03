<script setup lang="ts">
import DocumentManager from "../../components/document/DocumentManager.vue";
</script>

<template>
  <main class="documents-page">
    <header class="page-intro">
      <p class="section-code">R1 / DOCUMENTS</p>
      <h1>每一篇文档<br />都有清楚的状态</h1>
      <p>查看解析与索引进度，定位失败原因，并安全地重新排入任务队列。</p>
    </header>
    <DocumentManager />
  </main>
</template>

<style scoped>
.documents-page { width: min(100% - 2rem, 1160px); margin: 0 auto; padding: 1.6rem 0 2.4rem; }
.page-intro { max-width: 760px; margin-bottom: 1.25rem; }
.section-code { color: #b45f36; font-weight: 900; letter-spacing: 0.14em; }
.page-intro h1 { margin: 0.35rem 0 .7rem; color: #183b3a; font-family: Georgia, serif; font-size: clamp(2rem, 3.2vw, 3rem); font-weight: 600; line-height: 1.1; }
.page-intro p:last-child { color: #53686b; font-size: .98rem; line-height: 1.6; }
</style>
