<script setup lang="ts">
import type { DirectionCandidate } from "../../types/research-prototype";
defineProps<{ candidates: DirectionCandidate[] }>();
const emit = defineEmits<{ createPresentation: [candidate: DirectionCandidate] }>();
</script>

<template>
  <section class="candidates"><div class="section-heading"><div><p class="eyebrow">CANDIDATE DIRECTIONS · MOCK</p><h2>候选方向</h2><p>候选方向用于讨论，不构成研究决策或创新保证。</p></div><button class="secondary">选择证据矩阵（原型）</button></div>
    <article v-for="candidate in candidates" :key="candidate.id" class="candidate-card"><div class="candidate-title"><h3>{{ candidate.title }}</h3><button class="primary" @click="emit('createPresentation', candidate)">创建导师讨论组会</button></div><dl><div><dt>科学问题</dt><dd>{{ candidate.question }}</dd></div><div><dt>文献依据</dt><dd>{{ candidate.evidence }}</dd></div><div><dt>争议</dt><dd>{{ candidate.controversy }}</dd></div><div><dt>可行性</dt><dd>{{ candidate.feasibility }}</dd></div></dl><div class="risk"><strong>风险提示</strong><span>{{ candidate.risk }}</span></div><footer><span>下一步检索：{{ candidate.searchNext }}</span><span>导师确认：{{ candidate.advisorCheck }}</span></footer></article>
  </section>
</template>

<style scoped>.candidates{margin-top:1.2rem}.section-heading,.candidate-title{display:flex;justify-content:space-between;gap:1rem;align-items:start}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.section-heading h2,.candidate-title h3{margin:.25rem 0}.section-heading p{margin:.35rem 0;color:var(--text-muted)}button{border-radius:7px;padding:.55rem .75rem;font-weight:750;cursor:pointer}.secondary{border:1px solid var(--border-strong);background:var(--paper)}.primary{border:0;background:var(--color-primary);color:#fff}.candidate-card{margin-top:.8rem;padding:1rem 1.1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper)}dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin:1rem 0}dt{font-size:.78rem;font-weight:800;color:var(--text-muted)}dd{margin:.2rem 0 0;line-height:1.55}.risk{display:flex;gap:.65rem;padding:.65rem .75rem;background:var(--color-warning-soft);color:var(--color-warning);border-radius:6px}.candidate-card footer{display:flex;gap:1rem;justify-content:space-between;margin-top:.8rem;color:var(--text-muted);font-size:.86rem}@media(max-width:720px){.section-heading,.candidate-title,.candidate-card footer{display:block}.secondary,.primary{margin-top:.6rem}dl{grid-template-columns:1fr}.risk{display:block}.risk span{display:block;margin-top:.25rem}}</style>
