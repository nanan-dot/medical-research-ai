<script setup lang="ts">
const props = defineProps<{
  activeStep: number;
}>();

const emit = defineEmits<{
  select: [step: number];
}>();

const steps = ["研究问题", "检索意图", "术语与 MeSH", "检索与结果"];
</script>

<template>
  <nav
    class="strategy-stepper"
    aria-label="策略构建步骤"
  >
    <ol>
      <li
        v-for="(label, index) in steps"
        :key="label"
      >
        <button
          type="button"
          :aria-current="props.activeStep === index + 1 ? 'step' : undefined"
          :class="{ active: props.activeStep === index + 1 }"
          @click="emit('select', index + 1)"
        >
          <span aria-hidden="true">{{ index + 1 }}</span>{{ label }}
        </button>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.strategy-stepper { overflow-x: auto; }.strategy-stepper ol { display: grid; grid-template-columns: repeat(4,minmax(9rem,1fr)); gap: 8px; min-width: 36rem; margin: 0; padding: 0; list-style: none; }.strategy-stepper button { display: flex; gap: 8px; align-items: center; width: 100%; min-height: 40px; border: 0; border-bottom: 2px solid var(--border-subtle); background: transparent; color: var(--text-muted); font: inherit; font-size: .85rem; cursor: pointer; }.strategy-stepper button span { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; background: var(--surface-muted); }.strategy-stepper button.active { border-color: var(--color-primary); color: var(--color-primary); font-weight: 700; }.strategy-stepper button.active span { background: var(--color-primary); color: #fff; }.strategy-stepper button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
</style>
