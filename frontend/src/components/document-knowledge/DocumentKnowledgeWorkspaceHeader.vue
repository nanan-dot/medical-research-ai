<script setup lang="ts">
defineProps<{ active: "sources" | "documents"; description: string }>();
</script>

<template>
  <header class="workspace-header">
    <h1 class="workspace-title">文档与知识</h1>
    <p class="workspace-description">{{ description }}</p>
    <nav aria-label="文档与知识二级导航" class="workspace-tabs">
      <RouterLink to="/sources" :class="{ active: active === 'sources' }">知识库</RouterLink>
      <RouterLink to="/documents" :class="{ active: active === 'documents' }">文档库</RouterLink>
    </nav>
  </header>
</template>

<style scoped>
.workspace-header { border-bottom: 1px solid var(--border-subtle); }
.workspace-title { margin: 0; color: #10213d; font-size: clamp(1.75rem, 2.5vw, 2rem); font-weight: 700; line-height: 1.2; letter-spacing: -.02em; }
.workspace-description { margin: .45rem 0 1rem; color: var(--text-muted); font-size: .9rem; }
.workspace-tabs { display: flex; gap: 2rem; }
.workspace-tabs a { display: inline-block; padding: .55rem .15rem .7rem; border-bottom: 2px solid transparent; color: var(--text-muted); font-weight: 700; text-decoration: none; }
.workspace-tabs a.active { border-color: var(--color-primary); color: var(--color-primary); }
</style>
