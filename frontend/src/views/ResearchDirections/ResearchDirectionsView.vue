<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { evidenceMatricesApi, type EvidenceMatrix } from "../../api/evidenceMatrices";
import { researchDirectionsApi, type ResearchConditionsPayload, type ResearchDirection } from "../../api/researchDirections";
import CandidateDirectionGrid from "../../components/research/CandidateDirectionGrid.vue";
import ResearchContextForm from "../../components/research/ResearchContextForm.vue";

const matrices = ref<EvidenceMatrix[]>([]); const selectedMatrixId = ref<number | null>(null); const candidates = ref<ResearchDirection[]>([]); const saving = ref(false); const loadingDetailsId = ref<number | null>(null); const error = ref("");
const canGenerate = computed(() => selectedMatrixId.value !== null && !saving.value);
async function loadMatrices(): Promise<void> { try { const page = await evidenceMatricesApi.list(); matrices.value = page.items; selectedMatrixId.value = page.items[0]?.id ?? null; } catch (cause) { error.value = cause instanceof Error ? cause.message : "无法读取证据矩阵。"; } }
async function saveConditions(payload: ResearchConditionsPayload): Promise<void> { saving.value = true; error.value = ""; try { const conditions = await researchDirectionsApi.createConditions(payload); if (!selectedMatrixId.value) { error.value = "研究条件已保存；请先创建并选择一个证据矩阵，再生成候选方向。"; return; } candidates.value = await researchDirectionsApi.generate(conditions.id, selectedMatrixId.value, 3); } catch (cause) { error.value = cause instanceof Error ? cause.message : "无法生成候选研究方向。"; } finally { saving.value = false; } }
async function loadDetails(candidate: ResearchDirection): Promise<void> { loadingDetailsId.value = candidate.id; error.value = ""; try { const detailed = candidate.methods ? await researchDirectionsApi.getDetails(candidate.id) : await researchDirectionsApi.generateDetails(candidate.id); candidates.value = candidates.value.map((item) => item.id === detailed.id ? detailed : item); } catch (cause) { error.value = cause instanceof Error ? cause.message : "无法读取研究方向详情。"; } finally { loadingDetailsId.value = null; } }
onMounted(() => void loadMatrices());
</script>

<template>
  <main class="page"><header class="page-header"><div><p class="eyebrow">RESEARCH DIRECTION · LIVE</p><h1>研究方向</h1><p>以已选择的证据矩阵和明确录入的研究条件生成可讨论的候选方向；系统不会将未知条件补为事实。</p></div><label class="matrix-picker"><span>证据矩阵</span><select v-model="selectedMatrixId"><option :value="null">请选择</option><option v-for="matrix in matrices" :key="matrix.id" :value="matrix.id">{{ matrix.name }}</option></select></label></header>
    <p v-if="!matrices.length" class="notice">尚无可用证据矩阵。请先在“证据矩阵”中创建并补充文档。</p><p v-if="error" class="error">{{ error }}</p>
    <ResearchContextForm @submit="saveConditions" />
    <p v-if="saving" class="loading">正在基于真实接口生成候选方向…</p><CandidateDirectionGrid v-if="candidates.length" :candidates="candidates" :loading-details-id="loadingDetailsId" @details="loadDetails" />
    <section v-else-if="!saving" class="empty"><h2>尚未生成候选方向</h2><p>选择一个证据矩阵、填写至少一项研究条件后保存，即可请求后端生成候选项。</p></section>
  </main>
</template>

<style scoped>
.page{padding:2rem 1.4rem;max-width:1400px}.page-header{display:flex;justify-content:space-between;gap:1.2rem;margin-bottom:1.2rem}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.page-header h1{margin:.25rem 0;font-size:2.3rem}.page-header p{max-width:680px;color:var(--text-muted);line-height:1.6}.matrix-picker{display:grid;align-content:start;gap:.3rem;min-width:190px;font-size:.8rem;font-weight:800;color:var(--text-muted)}select{padding:.55rem .65rem;border:1px solid var(--border-subtle);border-radius:7px;background:var(--paper);font:inherit;color:var(--text-primary)}.notice,.error,.empty{padding:.8rem 1rem;border-radius:7px}.notice{background:var(--color-warning-soft);color:var(--color-warning)}.error{background:var(--color-danger-soft);color:var(--color-danger)}.empty{margin-top:1.2rem;border:1px dashed var(--border-strong);color:var(--text-muted)}.loading{margin-top:1rem;color:var(--text-muted)}@media(max-width:720px){.page-header{display:block}.matrix-picker{margin-top:1rem}}
</style>
