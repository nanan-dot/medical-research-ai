<script setup lang="ts">
import { computed } from "vue";
import BaseIcon from "../../components/ui/BaseIcon.vue";
import type { SearchStrategyDraft } from "../../types/searchStrategy";
import { strategyIntent } from "./strategyIntent";

const props = defineProps<{ strategy: SearchStrategyDraft }>();
const emit = defineEmits<{ regenerate: [] }>();
const intent = computed(() => strategyIntent(props.strategy));
</script>

<template>
  <section
    class="strategy-basis"
    aria-labelledby="strategy-basis-title"
  >
    <header>
      <h2 id="strategy-basis-title"><BaseIcon name="document" />策略依据</h2>
      <button
        type="button"
        title="返回入口，以当前研究问题为基础重新生成策略"
        @click="emit('regenerate')"
      >
        编辑
      </button>
    </header>
    <div class="question">
      <strong>研究问题</strong>
      <p>{{ props.strategy.research_question }}</p>
    </div>
    <div class="intent">
      <strong class="intent-mode">{{ intent.label }}</strong>
      <div
        class="intent-grid"
        :class="{ 'intent-concepts': props.strategy.intent_mode !== 'pico' }"
      >
        <article
          v-for="field in intent.fields"
          :key="field.key"
        >
          <span :class="`intent-${field.key.toLowerCase()}`">{{
            props.strategy.intent_mode === "pico" ? field.key : "•"
          }}</span>
          <div>
            <b>{{ field.label }}</b>
            <p>{{ field.value || "尚未明确" }}</p>
          </div>
        </article>
      </div>
    </div>
    <p
      v-if="!intent.complete"
      class="intent-helper"
    >
      研究意图尚未完整确认，可通过“编辑”补充；已有关键词保持不变。
    </p>
  </section>
</template>

<style scoped>
.strategy-basis {
  box-sizing: border-box;
  display: grid;
  gap: 0;
  padding: 0 18px 14px;
  border: 1px solid #dbe5f2;
  border-radius: 12px;
  background: var(--surface);
  box-shadow: 0 8px 22px rgb(32 73 125 / 7%);
  overflow: hidden;
}
.strategy-basis header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 0 8px;
}
h2,
p {
  margin: 0;
}
h2 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
}
h2 .icon {
  box-sizing: content-box;
  width: 15px;
  height: 15px;
  padding: 3px;
  border-radius: 3px;
  background: #0b66f6;
  color: #fff;
}
button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #d7e3f1;
  border-radius: 8px;
  background: var(--surface);
  color: #0b66f6;
  font: inherit;
  font-weight: 700;
}
.question,
.intent {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  border-inline: 1px solid #e4ebf6;
}
.question {
  border-top: 1px solid #e4ebf6;
  border-radius: 9px 9px 0 0;
  overflow: hidden;
}
.intent { border-bottom: 1px solid #e4ebf6; border-radius: 0 0 9px 9px; overflow: hidden; }
.question strong,
.intent > strong {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  background: #f5f8fc;
  color: var(--text-primary);
  font-size: 14px;
}
.question p {
  padding: 14px 20px;
  line-height: 20px;
  overflow-wrap: anywhere;
}
.intent-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 6px 12px 10px;
}
.intent-grid article {
  min-width: 0;
  display: flex;
  gap: 8px;
  padding: 12px 10px;
  border: 1px solid #dbe5f2;
  border-radius: 8px;
  background: var(--surface);
}
.intent-grid span {
  flex: 0 0 26px;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--color-primary);
  font-weight: 700;
}
.intent-grid .intent-i {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.intent-grid .intent-p { background: #0866ff; color: #fff; }
.intent-grid .intent-c {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.intent-grid .intent-o {
  background: #f1edff;
  color: #7048c8;
}
.intent-grid b {
  font-size: 13px;
  overflow-wrap: anywhere;
}
.intent-grid p {
  margin-top: 3px;
  color: var(--text-primary);
  font-size: 13px;
}
.intent-mode { overflow-wrap: anywhere; }
.intent-grid p { overflow-wrap: anywhere; }
.intent-grid article > div { min-width: 0; }
.intent-grid.intent-concepts { grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); }
.intent-helper { padding: 8px 20px; color: var(--text-muted); font-size: 12px; border-top: 1px solid var(--border-subtle); }
button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
@media (max-width: 1024px) {
  .intent-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .question,
  .intent {
    grid-template-columns: 1fr;
  }
  .question strong,
  .intent > strong {
    padding-bottom: 8px;
  }
  .question p {
    padding-top: 8px;
  }
  .intent-grid {
    grid-template-columns: 1fr;
  }
}
</style>
