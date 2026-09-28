<script setup lang="ts">
import { computed, nextTick, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import QuickStartTemplates from "../../components/search-entry/QuickStartTemplates.vue";
import ResearchQuestionComposer from "../../components/search-entry/ResearchQuestionComposer.vue";
import SearchEntryHero from "../../components/search-entry/SearchEntryHero.vue";
import SearchEntryUtilityLinks from "../../components/search-entry/SearchEntryUtilityLinks.vue";
import SearchModeSelector from "../../components/search-entry/SearchModeSelector.vue";
import SearchProcessIndicator from "../../components/search-entry/SearchProcessIndicator.vue";
import SearchTrustBar from "../../components/search-entry/SearchTrustBar.vue";
import { useSearchQuestionHistory } from "../../composables/useSearchQuestionHistory";
import { useSearchStrategyCreator } from "../../composables/useSearchStrategyCreator";
import type { SearchMode, SearchTemplate } from "../../types/searchEntry";
const route=useRoute(); const router=useRouter(); const question=shallowRef(typeof route.query.raw_topic==="string"?route.query.raw_topic:""); const mode=shallowRef<SearchMode>("auto");
const templates:SearchTemplate[]=[{id:"pico",title:"临床干预研究（PICO）",mode:"pico",description:"评估治疗、药物、手术等干预措施",question:"阿司匹林对冠心病患者的影响"},{id:"peco",title:"观察性研究（PECO）",mode:"peco",description:"研究暴露因素与疾病结局的关系",question:"吸烟与肺癌风险的关联研究"},{id:"disease",title:"疾病主题检索",mode:"disease",description:"围绕特定疾病或病症的综合文献",question:"糖尿病并发症的研究进展"},{id:"mechanism",title:"机制与基础研究",mode:"mechanism",description:"探索疾病机制、分子通路、基因表达",question:"炎症反应相关信号通路研究"}];
const { stage, error, isSubmitting, create } = useSearchStrategyCreator(); const canSubmit=computed(()=>question.value.trim().length>0&&!isSubmitting.value);
const { historyQuestions, rememberQuestion } = useSearchQuestionHistory();
watch(()=>route.query.raw_topic,(value)=>{if(typeof value==="string")question.value=value;});
async function submit():Promise<void>{if(!canSubmit.value)return;const submittedQuestion=question.value.trim();const result=await create(submittedQuestion,mode.value);if(!result)return;rememberQuestion(submittedQuestion,mode.value);await router.push({path:"/literature-search/workspace",query:{strategy_id:String(result.strategyId),raw_topic:result.parsed.raw_topic,entry_mode:mode.value,boolean_query:result.built.boolean_query}});}
function selectTemplate(template:SearchTemplate):void{mode.value=template.mode;question.value=template.question;void nextTick(()=>document.getElementById("search-entry-question")?.focus());}
function selectHistoricalQuestion(entry: { question: string; mode: SearchMode }): void { question.value=entry.question; mode.value=entry.mode; }
</script>
<template>
  <div class="search-entry">
    <SearchEntryUtilityLinks /><SearchEntryHero /><SearchProcessIndicator :stage="stage" /><div class="entry-content">
      <ResearchQuestionComposer
        v-model="question"
        :disabled="!canSubmit"
        :error="error"
        :history-questions="historyQuestions"
        @submit="submit"
        @select-history="selectHistoricalQuestion"
      >
        <SearchModeSelector v-model="mode" />
      </ResearchQuestionComposer><QuickStartTemplates
        :templates="templates"
        @select="selectTemplate"
      /><SearchTrustBar />
    </div><p
      class="stage"
      aria-live="polite"
    >
      {{ stage === "idle" ? "" : stage === "parse" ? "正在理解研究问题" : stage === "expand" ? "正在准备医学术语" : stage === "build" ? "正在构建检索策略" : stage === "handoff" ? "正在打开策略工作台" : "生成失败" }}
    </p>
  </div>
</template>
<style scoped>
.search-entry {
  --entry-content-width: 1180px;
  min-height: 100vh;
  background: #f7f9fd;
}

.entry-content {
  box-sizing: border-box;
  width: min(calc(100% - 64px), var(--entry-content-width));
  margin: 0 auto;
  padding: 0 0 36px;
  display: grid;
  gap: 28px;
}

.question-card { margin-top: 0; }
.stage { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
:global(.shell:has(.search-entry) .topbar) { display: none; }
@media (max-width: 767px) {
  .entry-content { width: min(calc(100% - 32px), var(--entry-content-width)); padding-bottom: 24px; gap: 24px; }
}
</style>
