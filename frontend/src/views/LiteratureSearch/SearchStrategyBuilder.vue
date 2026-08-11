<script setup lang="ts">
import { computed } from "vue";

export interface PicoState {
  population: string;
  intervention: string;
  comparison: string;
  outcome: string;
}

const props = defineProps<{
  loading: boolean;
  error: string | null;
  pico: PicoState;
  topic: string;
}>();

const emit = defineEmits<{
  submit: [topic: string];
  picoChange: [pico: PicoState];
  topicChange: [topic: string];
  clear: [];
}>();

const topicModel = computed({
  get: () => props.topic,
  set: (value: string) => emit("topicChange", value),
});

const displayError = computed(() => {
  if (!props.error) return "";
  if (typeof props.error === "string") return props.error;
  const detail = (props.error as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : "请求失败，请稍后重试。";
});

function field(fieldName: keyof PicoState) {
  return computed({
    get: () => props.pico[fieldName],
    set: (value: string) => emit("picoChange", { ...props.pico, [fieldName]: value }),
  });
}

function submitForm(): void {
  const value = topicModel.value.trim();
  if (value) emit("submit", value);
}

const population = field("population");
const intervention = field("intervention");
const comparison = field("comparison");
const outcome = field("outcome");
</script>

<template>
  <section class="strategy-builder" aria-labelledby="strategy-builder-title">
    <header class="panel-heading">
      <span class="evidence-track" aria-hidden="true" />
      <h2 id="strategy-builder-title">1. 输入研究问题</h2>
    </header>

    <form class="topic-section" @submit.prevent="submitForm">
      <label for="research-topic" class="topic-label">临床研究问题</label>
      <div class="topic-input-row">
        <input
          id="research-topic"
          v-model="topicModel"
          type="text"
          maxlength="1000"
          placeholder="例如：胃癌患者接受 EGFR 靶向治疗能否改善总体生存？"
          :disabled="props.loading"
        />
        <button
          type="submit"
          class="parse-action"
          :disabled="props.loading || !topicModel.trim()"
        >
          {{ props.loading ? "解析中…" : "解析研究问题" }}
        </button>
      </div>
      <p>系统将提取 PICO 条件并生成可编辑的检索式。</p>
    </form>

    <section class="pico-section" aria-labelledby="pico-fields-title">
      <div class="pico-section-heading">
        <h3 id="pico-fields-title">解析后的 PICO 条件</h3>
        <button type="button" class="clear-action" @click="emit('clear')">清空</button>
      </div>
      <p class="pico-hint">解析后可核对和手动修正；也可直接补充已知条件。</p>
      <div class="pico-fields" role="group" aria-labelledby="pico-fields-title">
      <label class="pico-field">
        <span>人群（P）</span>
        <input v-model="population" type="text" placeholder="解析后自动回填，或手动输入" />
      </label>
      <label class="pico-field">
        <span>干预（I）</span>
        <input v-model="intervention" type="text" placeholder="解析后自动回填，或手动输入" />
      </label>
      <label class="pico-field">
        <span>对照（C）</span>
        <input v-model="comparison" type="text" placeholder="解析后自动回填，或手动输入" />
      </label>
      <label class="pico-field">
        <span>结局（O）</span>
        <input v-model="outcome" type="text" placeholder="解析后自动回填，或手动输入" />
      </label>
      </div>
    </section>

    <p v-if="displayError" class="request-error" role="alert">{{ displayError }}</p>
  </section>
</template>

<style scoped>
.strategy-builder { display: grid; align-content: start; gap: 12px; padding: 16px; background: var(--surface, #fff); border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 8px; box-shadow: 0 8px 24px rgb(15 42 67 / 5%); }
.panel-heading { display: flex; gap: .55rem; align-items: center; }
.panel-heading h2 { margin: 0; color: var(--text-primary, #0f2a43); font-size: 1rem; line-height: 1.3; }
.evidence-track { width: 3px; height: 1.25rem; border-radius: 2px; background: var(--color-primary, #2563eb); }
.topic-input-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; }
.parse-action { min-height: 2.4rem; padding: .48rem .8rem; border: 0; border-radius: 6px; background: var(--color-primary, #2563eb); color: #fff; font: inherit; font-size: .85rem; font-weight: 600; cursor: pointer; white-space: nowrap; }
.parse-action:disabled { opacity: .55; cursor: not-allowed; }
.parse-action:active { transform: translateY(1px); }
.pico-section { display: grid; gap: 8px; padding-top: 12px; border-top: 1px solid var(--border-subtle, #dbe4f0); }
.pico-section-heading { display: flex; align-items: center; gap: 8px; }
.pico-section-heading h3 { margin: 0; color: var(--text-primary, #0f2a43); font-size: .85rem; }
.pico-hint { margin: 0; color: var(--text-muted, #64748b); font-size: .75rem; line-height: 1.45; }
.pico-fields { display: grid; gap: .48rem; }
.pico-field { display: grid; grid-template-columns: 5.75rem minmax(0, 1fr); gap: .55rem; align-items: center; color: var(--text-secondary, #475569); font-size: .85rem; }
.pico-field span { font-weight: 600; white-space: nowrap; }
.pico-field input, .topic-section input { min-width: 0; min-height: 2.4rem; padding: .48rem .65rem; border: 1px solid var(--border-strong, #cbd5e1); border-radius: 6px; background: #fff; color: var(--text-primary, #0f2a43); font: inherit; }
.pico-field input:focus-visible, .topic-section input:focus-visible, .clear-action:focus-visible, .parse-action:focus-visible { outline: 2px solid var(--color-primary, #2563eb); outline-offset: 2px; }
.clear-action { padding: 0; border: 0; background: transparent; color: var(--color-primary, #2563eb); font: inherit; font-size: .8rem; cursor: pointer; }
.topic-section { display: grid; gap: .42rem; }
.topic-label { color: var(--text-secondary, #475569); font-size: .85rem; font-weight: 600; }
.topic-section p { margin: 0; color: var(--text-muted, #64748b); font-size: .75rem; line-height: 1.45; }
.request-error { margin: 0; padding: .55rem .7rem; border-radius: 6px; background: var(--color-danger-soft, #fef2f2); color: var(--color-danger, #dc2626); font-size: .82rem; }
@media (max-width: 1280px) { .topic-input-row { grid-template-columns: 1fr; }.parse-action { justify-self: start; } }
@media (max-width: 640px) { .strategy-builder { padding: 1rem; } .parse-action { width: 100%; }.pico-field { grid-template-columns: 5rem minmax(0, 1fr); } }
</style>
