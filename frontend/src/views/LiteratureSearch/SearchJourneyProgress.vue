<script setup lang="ts">
const props = defineProps<{ activeStep: number; intentConfirmed?: boolean }>();
const isDone = (index: number) => index + 1 < props.activeStep && !(index === 1 && props.intentConfirmed === false);
const labels = ["输入研究问题", "理解研究意图", "构建检索策略", "开始检索"];
</script>

<template>
  <nav
    class="journey"
    aria-label="检索策略进度"
    tabindex="0"
  >
    <ol>
      <li
        v-for="(label, index) in labels"
        :key="label"
        :class="{
          done: isDone(index),
          active: index + 1 === props.activeStep,
        }"
      >
        <span
          :aria-current="index + 1 === props.activeStep ? 'step' : undefined"
        >{{ isDone(index) ? "✓" : index + 1 }}</span>
        {{ label }}
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.journey {
  min-width: 0;
  min-height: 62px;
  padding: 0 26px;
  overflow-x: auto;
  background: var(--surface);
}
.journey ol {
  display: grid;
  grid-template-columns: repeat(4, minmax(145px, 1fr));
  gap: 0;
  min-width: 660px;
  margin: 0;
  padding: 14px clamp(0px, 5vw, 98px);
  list-style: none;
}
.journey li {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 14px;
  white-space: nowrap;
}
.journey li:not(:last-child)::after {
  position: absolute;
  z-index: 0;
  top: 14px;
  left: 146px;
  right: 20px;
  border-top: 1px dashed #bdd0e8;
  content: "";
}
.journey span {
  flex: 0 0 28px;
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid #c9d7e9;
  border-radius: 999px;
  background: var(--surface);
}
.journey .done {
  color: var(--color-success);
}
.journey .done span {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.journey .active {
  color: var(--text-primary);
  font-weight: 700;
}
.journey .active span {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #fff;
}
.journey:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -2px; }
@media (max-width: 1120px) { .journey ol { padding-inline: 0; } }
</style>
