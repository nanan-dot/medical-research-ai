<template>
  <section class="skeleton" role="status" aria-live="polite" aria-label="正在检索推荐文献">
    <div v-for="row in 3" :key="row" class="skeleton-row"><span class="rank" /><div><span class="title" /><span class="meta" /><span class="action" /></div><span class="reason" /></div>
  </section>
</template>

<style scoped>
.skeleton{overflow:hidden;border:1px solid var(--border-subtle);border-radius:8px;background:var(--surface)}.skeleton-row{display:grid;grid-template-columns:28px minmax(0,1fr) 240px;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-subtle)}.skeleton-row:last-child{border:0}.skeleton span{display:block;border-radius:4px;background:var(--surface-muted)}.rank{height:24px}.title{height:16px;width:72%}.meta{height:12px;width:52%;margin-top:8px}.action{height:20px;width:96px;margin-top:12px}.reason{height:72px}@media(max-width:900px){.skeleton-row{grid-template-columns:28px minmax(0,1fr)}.reason{grid-column:2;height:40px}}
</style>
