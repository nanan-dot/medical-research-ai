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
.knowledge-page { width: min(100% - 2rem, 980px); margin: 0 auto; padding: 4rem 0; }
.page-intro { max-width: 700px; margin-bottom: 2rem; }
.section-code { color: #b45f36; font-weight: 900; letter-spacing: 0.14em; }
.page-intro h1 { margin: 0.4rem 0 1rem; color: #183b3a; font-family: Georgia, serif; font-size: clamp(2.4rem, 7vw, 4.8rem); font-weight: 500; line-height: 0.98; }
.page-intro p:last-child { max-width: 620px; color: #53686b; font-size: 1.05rem; line-height: 1.7; }
</style>
