<script setup lang="ts">
import { ref } from "vue";
import { paperAnalysisApi, type PaperAnalysis } from "../../api/paperAnalysis";

const documentId = ref<number | null>(null);
const analysis = ref<PaperAnalysis | null>(null);
const loading = ref(false);
const error = ref("");
const labels: Record<string, string> = {
  basic_information: "基本信息", one_sentence_conclusion: "一句话结论", research_background: "研究背景",
  research_question: "研究问题", study_type: "研究类型", population: "研究对象", sample_size: "样本量",
  intervention_or_exposure: "干预或暴露", comparator: "对照", primary_outcome: "主要结局",
  statistical_methods: "统计方法", main_results: "主要结果", innovations: "创新点", limitations: "局限",
  next_questions: "下一步问题", original_evidence: "原文证据", pending_items: "待确认项",
};

async function createAnalysis() {
  if (!documentId.value) return;
  loading.value = true; error.value = "";
  try { analysis.value = await paperAnalysisApi.create(documentId.value); }
  catch (reason) { error.value = reason instanceof Error ? reason.message : "分析失败"; }
  finally { loading.value = false; }
}
async function regenerate() {
  if (!analysis.value) return;
  loading.value = true;
  try { analysis.value = await paperAnalysisApi.regenerate(analysis.value.id); }
  finally { loading.value = false; }
}
</script>

<template>
  <main class="analysis-shell">
    <header><p class="eyebrow">SINGLE PAPER READING</p><h1>单篇论文阅读报告</h1><p>从结论到方法，再回到证据。未检出的信息会明确标记，推断不会冒充原文事实。</p></header>
    <form class="analysis-start" @submit.prevent="createAnalysis"><label>已建立索引的文档 ID <input v-model.number="documentId" type="number" min="1" required /></label><button :disabled="loading">{{ loading ? "分析中…" : "生成报告" }}</button></form>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <section v-if="analysis?.structured_result" class="report">
      <div class="report-actions"><span>第 {{ analysis.generation }} 版 · {{ analysis.template_version }}</span><button @click="regenerate">重新生成</button><a :href="paperAnalysisApi.exportUrl(analysis.id)">导出 Markdown</a></div>
      <article v-for="(field, name) in analysis.structured_result" :key="name"><div><h2>{{ labels[name] ?? name }}</h2><span :class="['claim', field.kind]">{{ field.kind }}</span></div><p>{{ field.value }}</p><ul v-if="field.source_indices.length"><li v-for="index in field.source_indices" :key="index">{{ analysis.sources[index]?.citation ?? analysis.sources[index]?.title ?? `来源 ${index + 1}` }}<template v-if="analysis.sources[index]?.page_start"> · 第 {{ analysis.sources[index].page_start }} 页</template></li></ul></article>
    </section>
  </main>
</template>

<style scoped>
.analysis-shell{max-width:920px;margin:auto;padding:4rem 1.2rem}.eyebrow{letter-spacing:.16em;color:#a94d2d;font-weight:800}h1{font:700 clamp(2.3rem,6vw,4.4rem)/1.05 Georgia,serif;color:#173f3c}.analysis-start,.report-actions{display:flex;align-items:end;gap:.7rem;padding:1rem;background:#fff;border:1px solid #d7dfda;border-radius:16px}.analysis-start label{display:grid;gap:.35rem;flex:1}.analysis-start input{padding:.7rem;border:1px solid #9cafaa;border-radius:8px}button,a{padding:.65rem .9rem;border:0;border-radius:8px;background:#173f3c;color:#fff;font-weight:700;text-decoration:none}.report{display:grid;gap:1rem;margin-top:1.5rem}.report-actions{align-items:center}.report-actions span{margin-right:auto}article{padding:1.2rem 1.4rem;background:#fff;border-left:4px solid #d8a347;border-radius:4px 14px 14px 4px}article>div{display:flex;align-items:center;gap:.7rem}h2{font-size:1.05rem}.claim{font-size:.7rem;text-transform:uppercase;padding:.2rem .45rem;border-radius:99px;background:#e9efec}.claim.inference{background:#fff0d2}.claim.not_found{background:#f4e5e2}.error{color:#9c2f2f}
</style>
