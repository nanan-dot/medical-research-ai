<script setup lang="ts">
// 构建检索策略：研究问题输入 + 生成检索式（真实 parse-query 管线）+ PICO 四条件。
// PICO 为受控状态：由父级持有并传入（解析回填/手动修订均经父级），
// 组件仅负责展示与输入事件，不伪造已保存到后端。
import { computed, ref } from "vue";

export interface PicoState {
  population: string;
  intervention: string;
  comparison: string;
  outcome: string;
}

const emit = defineEmits<{
  submit: [topic: string];
  picoChange: [pico: PicoState];
}>();

const props = defineProps<{
  loading: boolean;
  error: string | null;
  hasCandidate: boolean;
  pico: PicoState;
}>();

const topic = ref("");

function submitForm(): void {
  const text = topic.value.trim();
  if (!text) return; // 空输入前端拦截，不请求接口
  emit("submit", text);
}

// 错误信息健壮化：后端/请求库可能返回对象或非字符串，统一转为可读文本。
const displayError = computed(() => {
  if (!props.error) return "";
  if (typeof props.error === "string") return props.error;
  const detail = (props.error as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : "请求失败，请稍后重试。";
});

// 受控字段：读取来自 props，写入经 emit 通知父级更新（单向数据流）。
function field(fieldName: keyof PicoState) {
  return computed({
    get: () => props.pico[fieldName],
    set: (value: string) => emit("picoChange", { ...props.pico, [fieldName]: value }),
  });
}
const population = field("population");
const intervention = field("intervention");
const comparison = field("comparison");
const outcome = field("outcome");
</script>

<template>
  <section class="strategy-builder" aria-labelledby="strategy-builder-title">
    <h2 id="strategy-builder-title" class="section-title">构建检索策略</h2>
    <form class="question-row" @submit.prevent="submitForm">
      <label class="question-label">
        <span class="field-label-text">研究问题</span>
        <input
          v-model="topic"
          type="text"
          maxlength="1000"
          placeholder="例如：肝细胞癌一线免疫联合治疗能否改善总体生存？"
          :disabled="props.loading"
        />
      </label>
      <button class="primary-action" type="submit" :disabled="props.loading || !topic.trim()">
        {{ props.loading ? "解析中…" : "生成检索式" }}
      </button>
    </form>
    <p v-if="displayError" class="request-error" role="alert">{{ displayError }}</p>

    <div class="pico-grid" role="group" aria-label="PICO 检索条件">
      <label class="pico-field">
        <span class="field-label-text">人群</span>
        <input v-model="population" type="text" placeholder="例如：晚期肝细胞癌" />
      </label>
      <label class="pico-field">
        <span class="field-label-text">干预</span>
        <input v-model="intervention" type="text" placeholder="例如：PD-1/PD-L1 抑制剂联合治疗" />
      </label>
      <label class="pico-field">
        <span class="field-label-text">对照</span>
        <input v-model="comparison" type="text" placeholder="例如：索拉非尼或标准治疗" />
      </label>
      <label class="pico-field">
        <span class="field-label-text">结局</span>
        <input v-model="outcome" type="text" placeholder="例如：总体生存与安全性" />
      </label>
    </div>
  </section>
</template>

<style scoped>
.strategy-builder {
  display: grid;
  gap: 1rem;
  padding: 1.25rem;
  background: var(--surface, #fff);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
}
.section-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: 1.05rem;
}
.question-row {
  display: flex;
  gap: 0.6rem;
  align-items: flex-end;
}
.question-label {
  flex: 1;
  display: grid;
  gap: 0.35rem;
}
.field-label-text {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary, #475569);
}
.question-label input,
.pico-field input {
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--border-strong, #cbd5e1);
  border-radius: 6px;
  font: inherit;
  background: #fff;
}
.question-label input:focus-visible,
.pico-field input:focus-visible {
  outline: 2px solid var(--color-primary, #2563eb);
  outline-offset: 1px;
}
.primary-action {
  padding: 0.6rem 1.2rem;
  border: 0;
  border-radius: 6px;
  background: var(--color-primary, #2563eb);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.primary-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.pico-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  padding-top: 0.25rem;
}
.pico-field {
  display: grid;
  gap: 0.35rem;
}
.request-error {
  margin: 0;
  padding: 0.6rem 0.8rem;
  color: var(--color-danger, #dc2626);
  background: var(--color-danger-soft, #fef2f2);
  border-radius: 6px;
  font-size: 0.875rem;
}
@media (max-width: 960px) {
  .question-row {
    display: grid;
  }
  .pico-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .pico-grid {
    grid-template-columns: 1fr;
  }
}
</style>
