<script setup lang="ts">
import { useRouter } from "vue-router";
import CandidateDirectionGrid from "../../components/research/CandidateDirectionGrid.vue";
import ResearchContextForm from "../../components/research/ResearchContextForm.vue";
import { directionCandidates, researchConditions } from "../../mocks/research-prototype";
import type { DirectionCandidate } from "../../types/research-prototype";
const router = useRouter();
function createPresentation(candidate: DirectionCandidate) { void router.push({ path: "/presentations", query: { source: candidate.id, type: "开题或方向讨论" } }); }
</script>

<template><main class="page"><header class="page-header"><div><p class="eyebrow">RESEARCH DIRECTION · MOCK</p><h1>研究方向</h1><p>将研究条件、候选方向与导师确认项放在同一处；未知信息始终保留为未知。</p></div><div class="summary"><span>条件摘要</span><strong>12 项待确认</strong><small>候选不是最终决策</small></div></header><ResearchContextForm :conditions="researchConditions"/><CandidateDirectionGrid :candidates="directionCandidates" @create-presentation="createPresentation"/></main></template>

<style scoped>.page{padding:2rem 1.4rem;max-width:1400px}.page-header{display:flex;justify-content:space-between;gap:1.2rem;margin-bottom:1.2rem}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.page-header h1{margin:.25rem 0;font-size:2.3rem}.page-header p:last-child{max-width:680px;color:var(--text-muted);line-height:1.6}.summary{display:grid;align-content:start;gap:.22rem;min-width:170px;padding:.85rem 1rem;border-left:3px solid var(--color-primary);background:var(--surface-muted)}.summary span,.summary small{color:var(--text-muted);font-size:.8rem}.summary strong{font-size:1.15rem}@media(max-width:720px){.page-header{display:block}.summary{margin-top:1rem}}</style>
