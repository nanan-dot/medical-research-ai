<script setup lang="ts">
import { computed } from "vue";
import type { SearchStrategyDraft, StrategyCount, StrategyValidation } from "../../types/searchStrategy";
import { currentStrategyValidation, strategyReadiness } from "./strategyReadiness";

const props = defineProps<{
  strategy: SearchStrategyDraft;
  modelValue: string;
  validation: StrategyValidation | null;
  count: StrategyCount | null;
  loading: boolean;
  actionsDisabled?: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: string];
  validate: [];
  refreshCount: [];
  copy: [];
}>();
const validation = computed(() => currentStrategyValidation(props.strategy, props.modelValue, props.validation));
const readiness = computed(() => strategyReadiness(props.strategy, props.modelValue, props.validation));
const currentCount = computed(() => props.modelValue === props.strategy.query_text && props.count?.fingerprint === props.strategy.fingerprint ? props.count : null);
const validationMessage = computed(() => validation.value?.blocking_errors[0]?.message
  ?? (readiness.value.state === "blocked" ? "检索式未通过语法或字段检查。"
    : readiness.value.checks[3].passed ? "检索式语法与字段标签已验证。"
      : props.modelValue !== props.strategy.query_text ? "修改尚未保存，保存后请重新验证。" : "检索式尚未验证，可先验证再执行。"));
</script>

<template>
  <section
    class="strategy-query"
    aria-labelledby="strategy-query-title"
  >
    <header class="section-heading">
      <h2 id="strategy-query-title">PubMed 检索式预览（可编辑）</h2>
      <div class="heading-actions">
        <button
          type="button"
          :disabled="!props.modelValue"
          @click="emit('copy')"
        >
          复制检索式
        </button>
        <button
          type="button"
          :disabled="props.loading || props.actionsDisabled || !props.modelValue.trim()"
          @click="emit('validate')"
        >
          验证
        </button>
      </div>
    </header>
    <textarea
      id="strategy-query-text"
      class="query-editor"
      aria-label="PubMed 检索式"
      aria-describedby="strategy-query-status"
      :value="props.modelValue"
      :disabled="props.loading"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    />
    <div class="query-bottom">
      <div
        id="strategy-query-status"
        class="validation-details"
        aria-live="polite"
      >
        <p
          class="validation"
          :class="{ invalid: readiness.state === 'blocked' }"
        >
          {{ validationMessage }}
        </p>
        <ul
          v-if="validation?.warnings.length"
          class="validation-warnings"
        >
          <li
            v-for="(warning, index) in validation.warnings"
            :key="index"
          >
            {{ warning.message }}
          </li>
        </ul>
      </div>
      <div class="count">
        <span>PubMed 当前匹配</span>
        <strong v-if="currentCount">{{ currentCount.count }} 篇</strong>
        <strong v-else-if="props.strategy.count_state === 'success'">当前数值未载入，请刷新</strong>
        <strong v-else>待刷新</strong>
        <button
          type="button"
          :disabled="props.loading || props.actionsDisabled || !props.modelValue.trim()"
          @click="emit('refreshCount')"
        >
          刷新数量
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.strategy-query { min-width: 0; display: grid; gap: 4px; padding: 8px 18px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow-sm); }
.section-heading, .heading-actions, .query-bottom, .count { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px 12px; }
h2, p { margin: 0; }
h2 { font-size: 15px; }
.query-editor { box-sizing: border-box; width: 100%; min-width: 0; height: 50px; min-height: 50px; resize: vertical; border: 1px solid #e4eaf4; border-radius: 8px; padding: 6px 10px; background: #f7f9fc; color: var(--text-primary); font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.validation-details { min-width: 0; flex: 1 1 230px; }
.validation { color: var(--text-muted); font-size: 12px; overflow-wrap: anywhere; }
.validation.invalid { color: var(--color-danger); }
.validation-warnings { padding-left: 16px; margin: 4px 0 0; font-size: 12px; color: var(--color-warning); }
.count { color: var(--text-muted); font-size: 12px; }
.count strong { color: var(--text-primary); }
.count button, .heading-actions button { min-height: 24px; padding: 0 8px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); color: var(--color-primary); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; }
button:disabled, textarea:disabled { opacity: .55; cursor: not-allowed; }
button:focus-visible, textarea:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
@media (max-width:640px) { .section-heading, .query-bottom { align-items: stretch; flex-direction: column; } .validation-details { flex-basis: auto; } .count { justify-content: flex-start; } }
</style>
