<script setup lang="ts">
import KnowledgeSourceManager from "../../components/knowledge-source/KnowledgeSourceManager.vue";
</script>

<template>
  <main class="knowledge-page">
    <header class="page-intro">
      <p class="section-code">R1 / KNOWLEDGE BASE</p>
      <h1>让研究材料<br />保持在你的边界内</h1>
      <p>登记本地文件夹、Obsidian Vault 或临时导入目录。移除记录不会删除目录中的任何文件。</p>
    </header>
    <KnowledgeSourceManager />
  </main>
</template>

<style scoped>
.knowledge-page { width: min(100% - 2rem, 980px); margin: 0 auto; padding: 1.8rem 0 2.4rem; }
.page-intro { max-width: 700px; margin-bottom: 1.25rem; }
.section-code { color: #b45f36; font-weight: 900; letter-spacing: 0.14em; }
.page-intro h1 { margin: .35rem 0 .7rem; color: #183b3a; font-family: Georgia, serif; font-size: clamp(2rem, 3.3vw, 3rem); font-weight: 600; line-height: 1.1; }
.page-intro p:last-child { max-width: 620px; color: #53686b; font-size: .98rem; line-height: 1.6; }
</style>
