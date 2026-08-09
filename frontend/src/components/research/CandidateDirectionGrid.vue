<script setup lang="ts">
import type { ResearchDirection } from "../../api/researchDirections";
defineProps<{ candidates: ResearchDirection[]; loadingDetailsId: number | null }>();
const emit = defineEmits<{ details: [candidate: ResearchDirection] }>();
</script>

<template>
  <section class="candidates"><div class="section-heading"><div><p class="eyebrow">CANDIDATE DIRECTIONS · LIVE</p><h2>候选研究方向</h2><p>候选项来自所选证据矩阵，不构成创新性或发表结果保证。</p></div></div>
    <article v-for="candidate in candidates" :key="candidate.id" class="candidate-card">
      <div class="candidate-title"><div><h3>{{ candidate.name }}</h3><span class="priority">优先级：{{ candidate.priority }}</span></div><button :disabled="loadingDetailsId === candidate.id" @click="emit('details', candidate)">{{ candidate.methods ? "查看详情" : "生成详情" }}</button></div>
      <dl><div><dt>科学问题</dt><dd>{{ candidate.question }}</dd></div><div><dt>研究对象与类型</dt><dd>{{ candidate.research_object }} · {{ candidate.study_type }}</dd></div><div><dt>当前证据</dt><dd>{{ candidate.current_evidence.text }}</dd></div><div><dt>争议</dt><dd>{{ candidate.controversy.text }}</dd></div></dl>
      <p class="gap"><strong>证据缺口：</strong>{{ candidate.gap }}</p>
      <section v-if="candidate.methods" class="details"><p><strong>方法：</strong>{{ candidate.methods }}</p><p><strong>实施要求：</strong>{{ candidate.requirements }}</p><p><strong>风险：</strong>{{ candidate.time_risk }} / {{ candidate.resource_risk }} / {{ candidate.ethics_risk }}</p><p><strong>检索式：</strong>{{ candidate.search_terms }}</p><p><strong>建议与导师确认：</strong>{{ candidate.advisor_questions }}</p></section>
    </article>
  </section>
</template>

<style scoped>
.candidates{margin-top:1.2rem}.section-heading,.candidate-title{display:flex;justify-content:space-between;gap:1rem;align-items:start}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.section-heading h2,.candidate-title h3{margin:.25rem 0}.section-heading p{margin:.35rem 0;color:var(--text-muted)}.candidate-card{margin-top:.8rem;padding:1rem 1.1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper)}button{border:0;border-radius:7px;padding:.55rem .75rem;background:var(--color-primary);color:#fff;font:inherit;font-weight:750;cursor:pointer}.priority{color:var(--text-muted);font-size:.8rem}dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin:1rem 0}dt{font-size:.78rem;font-weight:800;color:var(--text-muted)}dd{margin:.2rem 0 0;line-height:1.55}.gap,.details{padding:.65rem .75rem;background:var(--surface-muted);border-radius:6px;line-height:1.55}.details{margin-top:.7rem}.details p{margin:.4rem 0}@media(max-width:720px){.candidate-title{display:block}.candidate-title button{margin-top:.6rem}dl{grid-template-columns:1fr}}
</style>
