<template>
  <div class="app-layout">
    <header class="topbar">
      <RouterLink class="brand" to="/">研证</RouterLink>
      <nav class="navigation" aria-label="主导航">
        <RouterLink to="/models">模型</RouterLink>
        <RouterLink to="/sources">知识源</RouterLink>
        <RouterLink to="/documents">文档</RouterLink>
        <RouterLink to="/literature-search">检索需求</RouterLink>
        <RouterLink to="/analysis">分析</RouterLink>
        <RouterLink to="/chat">问答</RouterLink>
        <RouterLink to="/feedback">反馈</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<style scoped>
.topbar { position: sticky; top: 0; z-index: 10; display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem; background: #eff4f0e8; backdrop-filter: blur(12px); }
.brand { font: 700 1.5rem Georgia, serif; color: #173f3c; text-decoration: none; }
.navigation { display: flex; gap: 0.25rem; overflow: auto; }
.navigation a { padding: 0.5rem 0.7rem; border-radius: 99px; color: #53686b; text-decoration: none; font-weight: 700; white-space: nowrap; }
.navigation a.router-link-active { background: #173f3c; color: #fff; }
@media (max-width: 640px) { .topbar { align-items: flex-start; flex-direction: column; } .navigation { width: 100%; } }
</style>
