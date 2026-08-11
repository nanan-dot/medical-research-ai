<script setup lang="ts">
import { computed, shallowRef } from "vue";

interface Props {
  abstractText: string | null;
}

const props = defineProps<Props>();
const isExpanded = shallowRef(false);
const hasAbstract = computed(() => Boolean(props.abstractText?.trim()));
</script>

<template>
  <div class="abstract-disclosure">
    <button v-if="hasAbstract" type="button" :aria-expanded="isExpanded" @click="isExpanded = !isExpanded">
      {{ isExpanded ? "收起摘要" : "展开摘要" }}
    </button>
    <p v-else>摘要不可用</p>
    <section v-if="isExpanded" class="abstract-content" aria-label="摘要内容">
      <h4 class="abstract-title">摘要</h4>
      <p class="abstract-text">{{ abstractText }}</p>
    </section>
  </div>
</template>

<style scoped>
.abstract-disclosure { display: grid; gap: .4rem; }
button { justify-self: start; min-height: 1.85rem; padding: .28rem .52rem; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); color: var(--color-primary); font: inherit; font-size: .78rem; font-weight: 600; cursor: pointer; }
button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
p { margin: 0; color: var(--text-muted); font-size: .78rem; }
.abstract-content { display: grid; gap: .4rem; margin-top: .15rem; padding: .72rem .8rem; border: 1px solid var(--border-subtle, #dbe4f0); border-left: 3px solid var(--color-primary, #2563eb); border-radius: 0 6px 6px 0; background: var(--surface-muted, #f8fafc); }
.abstract-title { margin: 0; color: var(--text-primary); font-size: .82rem; }
.abstract-text { white-space: pre-wrap; line-height: 1.6; color: var(--text-primary); }
</style>
