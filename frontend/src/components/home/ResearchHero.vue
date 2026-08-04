<script setup lang="ts">
defineProps<{ title: string; description: string }>();
</script>
<template>
  <section class="research-hero">
    <div class="hero-copy">
      <p class="eyebrow">RESEARCH WORKSPACE · {{ title }}</p>
      <h1>你的医学科研工作空间</h1>
      <p class="lead">{{ description }}</p>
    </div>
    <RouterLink class="continue-link" to="/documents">继续上次研究 →</RouterLink>
  </section>
</template>
<style scoped>
.research-hero{display:flex;align-items:flex-end;justify-content:space-between;gap:2rem}.hero-copy{min-width:0}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.13em}.research-hero h1{margin:.35rem 0 .25rem;color:var(--text-primary);font-size:clamp(1.6rem,2.6vw,2.3rem);line-height:1.15;letter-spacing:-.02em}.lead{margin:0;color:var(--text-muted);font-size:.95rem;line-height:1.6}.continue-link{flex-shrink:0;color:var(--color-primary);font-weight:700;text-decoration:none;font-size:.9rem}.continue-link:hover{text-decoration:underline}@media(max-width:700px){.research-hero{align-items:flex-start;flex-direction:column;gap:.6rem}}
</style>
