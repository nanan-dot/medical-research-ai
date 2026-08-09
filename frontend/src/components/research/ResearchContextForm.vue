<script setup lang="ts">
import { reactive } from "vue";
import type { ConditionField, ResearchConditionsPayload } from "../../api/researchDirections";

const emit = defineEmits<{ submit: [payload: ResearchConditionsPayload] }>();
const form = reactive({ specialty: "", advisorDirection: "", interestTopic: "", researchTypes: "", uncertainNotes: "" });

function optionalField(value: string): ConditionField | undefined {
  return value.trim() ? { value: value.trim(), known: true, source: "user" } : undefined;
}
function submit(): void {
  const payload: ResearchConditionsPayload = {
    specialty: optionalField(form.specialty), advisor_direction: optionalField(form.advisorDirection),
    interest_topic: optionalField(form.interestTopic), existing_papers: optionalField(form.researchTypes),
    uncertain_notes: form.uncertainNotes.trim() || undefined,
  };
  emit("submit", payload);
}
</script>

<template>
  <section class="form-card">
    <div class="section-heading"><div><p class="eyebrow">RESEARCH CONTEXT · LIVE</p><h2>研究条件</h2><p>只提交你明确提供的信息；空字段不会被自动补全为结论。</p></div></div>
    <form class="condition-grid" @submit.prevent="submit">
      <label><span>专业 / 学科</span><input v-model="form.specialty" maxlength="500" placeholder="例如：肿瘤学" /></label>
      <label><span>导师方向</span><input v-model="form.advisorDirection" maxlength="500" placeholder="可留空" /></label>
      <label><span>兴趣主题</span><input v-model="form.interestTopic" maxlength="500" placeholder="例如：肝癌免疫治疗" /></label>
      <label><span>已有研究或关键词</span><input v-model="form.researchTypes" maxlength="500" placeholder="可留空" /></label>
      <label class="wide"><span>不确定项说明</span><textarea v-model="form.uncertainNotes" maxlength="2000" placeholder="样本、设备、预算等暂未确认的信息可以如实记录。" /></label>
      <div class="actions"><button type="submit">保存研究条件</button></div>
    </form>
  </section>
</template>

<style scoped>
.form-card{padding:1.2rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper)}.section-heading h2{margin:.25rem 0}.section-heading p{margin:.3rem 0;color:var(--text-muted)}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.condition-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.8rem;margin-top:1rem}.condition-grid label{display:grid;gap:.28rem;font-size:.85rem;font-weight:700}.condition-grid input,.condition-grid textarea{min-width:0;padding:.58rem .65rem;border:1px solid var(--border-subtle);border-radius:6px;background:var(--surface-muted);font:inherit}.condition-grid textarea{min-height:78px;resize:vertical}.wide,.actions{grid-column:1/-1}.actions button{border:0;border-radius:7px;padding:.6rem .9rem;background:var(--color-primary);color:#fff;font:inherit;font-weight:750;cursor:pointer}@media(max-width:720px){.condition-grid{grid-template-columns:1fr}}
</style>
