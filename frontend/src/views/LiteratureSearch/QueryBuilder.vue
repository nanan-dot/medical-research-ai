<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import type { SearchIntentCandidate } from "../../api/literatureSearch";

interface Props {
  candidate: SearchIntentCandidate;
}

const props = defineProps<Props>();
const emit = defineEmits<{ updateCandidate: [candidate: SearchIntentCandidate] }>();

function cloneCandidate(value: SearchIntentCandidate): SearchIntentCandidate {
  return {
    ...value,
    date_range: value.date_range ? { ...value.date_range } : null,
    study_types: [...value.study_types],
    language: [...value.language],
    exclusions: [...value.exclusions],
  };
}

const draft = reactive<SearchIntentCandidate>(cloneCandidate(props.candidate));

watch(
  () => props.candidate,
  (next) => Object.assign(draft, cloneCandidate(next)),
  { deep: true },
);

function publish() {
  emit("updateCandidate", cloneCandidate(draft));
}

function updateList(field: "study_types" | "language" | "exclusions", value: string) {
  draft[field] = value.split(",").map((item) => item.trim()).filter(Boolean);
  publish();
}

const studyTypesText = computed({ get: () => draft.study_types.join(", "), set: (value: string) => updateList("study_types", value) });
const languageText = computed({ get: () => draft.language.join(", "), set: (value: string) => updateList("language", value) });
const exclusionsText = computed({ get: () => draft.exclusions.join(", "), set: (value: string) => updateList("exclusions", value) });
const startYear = computed({
  get: () => draft.date_range?.start_year ?? null,
  set: (value: number | null) => {
    if (!draft.date_range) draft.date_range = { start_year: null, end_year: null, original_expression: null };
    draft.date_range.start_year = value;
    publish();
  },
});
const endYear = computed({
  get: () => draft.date_range?.end_year ?? null,
  set: (value: number | null) => {
    if (!draft.date_range) draft.date_range = { start_year: null, end_year: null, original_expression: null };
    draft.date_range.end_year = value;
    publish();
  },
});
</script>

<template>
  <section class="query-builder" aria-labelledby="query-builder-title">
    <header class="builder-header">
      <div>
        <p class="eyebrow">EDIT BEFORE SEARCH</p>
        <h2 id="query-builder-title" class="builder-title">可编辑检索条件</h2>
      </div>
      <span class="candidate-note">这只是候选条件，不是最终检索式。</span>
    </header>
    <div class="field-grid">
      <label class="field-label">主题<input v-model="draft.topic" @change="publish" /></label>
      <label class="field-label">疾病<input v-model="draft.disease" @change="publish" /></label>
      <label class="field-label">干预或药物<input v-model="draft.intervention" @change="publish" /></label>
      <label class="field-label">靶点<input v-model="draft.target" @change="publish" /></label>
      <label class="field-label">机制<input v-model="draft.mechanism" @change="publish" /></label>
      <label class="field-label">最大结果数<input v-model.number="draft.retmax" min="1" max="500" type="number" @change="publish" /></label>
      <label class="field-label">开始年份<input v-model.number="startYear" min="1900" type="number" /></label>
      <label class="field-label">结束年份<input v-model.number="endYear" min="1900" type="number" /></label>
      <label class="field-label">研究类型（逗号分隔）<input v-model="studyTypesText" /></label>
      <label class="field-label">语言（逗号分隔）<input v-model="languageText" /></label>
      <label class="field-label field-wide">排除条件（逗号分隔）<input v-model="exclusionsText" /></label>
    </div>
  </section>
</template>

<style scoped>
.query-builder { display: grid; gap: 1rem; padding: 1.25rem; background: #fff; border-radius: 16px; }
.builder-header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; }
.eyebrow { margin: 0; color: #a94d2d; font-weight: 800; letter-spacing: .12em; }
.builder-title { margin: .25rem 0 0; color: #173f3c; }
.candidate-note { color: #53686b; font-size: .9rem; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; }
.field-label { display: grid; gap: .35rem; color: #40585a; font-weight: 700; }
.field-label input { padding: .65rem; border: 1px solid #aabbbb; border-radius: 8px; font: inherit; }
.field-wide { grid-column: 1 / -1; }
@media (max-width: 640px) { .builder-header, .field-grid { display: grid; grid-template-columns: 1fr; } .field-wide { grid-column: auto; } }
</style>
