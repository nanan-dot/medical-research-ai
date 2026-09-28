<script setup lang="ts">
import type { SearchStage } from "../../types/searchEntry";
const props = defineProps<{ stage: SearchStage }>();
const stages = ["输入研究问题", "理解研究意图", "构建检索策略", "开始检索"];
const activeIndex = () => ({ idle: 0, parse: 1, expand: 1, build: 2, handoff: 3, failed: 0 })[props.stage];
</script>
<template>
  <ol
    class="process"
    aria-label="检索流程"
  >
    <li
      v-for="(item,index) in stages"
      :key="item"
      :class="{active:index===activeIndex(),done:index<activeIndex()}"
    >
      <b>{{ index + 1 }}</b><span>{{ item }}</span>
    </li>
  </ol>
</template>
<style scoped>
.process {
  box-sizing: border-box;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  width: min(calc(100% - 64px), var(--entry-content-width, 1180px));
  min-height: 64px;
  margin: -1px auto 0;
  padding: 0 28px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 20px rgb(35 74 145 / .06);
  list-style: none;
}

.process li { display: flex; align-items: center; justify-content: center; gap: 10px; color: #6e7fa4; font-size: 14px; }
.process b { display: grid; place-items: center; width: 25px; height: 25px; border-radius: 50%; background: #e8edf8; font-size: 12px; }
.process .active { color: #215cf1; font-weight: 700; }
.process .active b, .process .done b { background: #245cf1; color: #fff; }

@media (max-width: 767px) {
  .process { width: min(calc(100% - 32px), var(--entry-content-width, 1180px)); height: auto; grid-template-columns: repeat(2, 1fr); padding: 6px 12px; }
  .process li { min-height: 42px; justify-content: start; font-size: 12px; }
}
</style>
