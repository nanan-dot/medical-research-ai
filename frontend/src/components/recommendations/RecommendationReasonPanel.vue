<script setup lang="ts">
import { computed } from "vue";
import type { RecommendationReason } from "../../api/recommendations";

const props = defineProps<{ reason: RecommendationReason }>();
const emit = defineEmits<{ explanation: [HTMLElement] }>();
const matches = computed(() =>
  props.reason.matches.filter(
    (match) => match.status === "matched" && match.matched_terms.length,
  ),
);
const excerpt = computed(
  () => matches.value.find((match) => match.excerpt)?.excerpt,
);
const specificLimitations = computed(() =>
  props.reason.limitations.filter(
    (limit) =>
      ![
        "intent_not_confirmed",
        "evidence_fit_unavailable",
        "evidence_review_needed",
      ].includes(limit.code),
  ),
);
const relevance = computed(
  () => props.reason.relevance || props.reason.narrative,
);
</script>

<template>
  <section class="reason" aria-label="推荐依据摘要">
    <div class="reason-heading">
      <span class="reason-label">推荐理由</span>
      <strong class="reason-title">{{ reason.headline }}</strong>
    </div>
    <p class="relevance">{{ relevance }}</p>
    <blockquote v-if="excerpt" class="evidence-excerpt">
      {{ excerpt }}
    </blockquote>
    <div class="reason-footer">
      <span v-if="reason.incremental_value" class="incremental">{{
        reason.incremental_value
      }}</span>
      <button
        type="button"
        class="evidence-button"
        @click="emit('explanation', $event.currentTarget as HTMLElement)"
      >
        ▧ 查看完整依据
      </button>
    </div>
    <details v-if="specificLimitations.length" class="limitations">
      <summary>{{ specificLimitations.length }} 项阅读提示</summary>
      <p v-for="limit in specificLimitations" :key="limit.code">
        {{ limit.message }}
      </p>
    </details>
  </section>
</template>

<style scoped>
.reason {
  min-width: 0;
  padding: 0 0 0 24px;
  border-left: 1px solid var(--border-subtle);
  background: transparent;
}
.reason-heading {
  display: flex;
  gap: 12px;
  align-items: baseline;
  flex-wrap: wrap;
}
.reason-label {
  flex: none;
  width: 100%;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-primary);
}
.reason-title {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  font-weight: 600;
  overflow-wrap: anywhere;
}
.relevance {
  margin: 5px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.evidence-excerpt {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.65;
  color: var(--text-muted);
  overflow-wrap: anywhere;
}
.reason-footer {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  margin-top: 8px;
}
.incremental {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.6;
}
.evidence-button {
  flex: none;
  border: 0;
  background: transparent;
  padding: 3px 0;
  color: var(--color-primary);
  font-size: 12px;
  cursor: pointer;
}
.evidence-button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}
.limitations {
  margin-top: 8px;
  color: var(--color-warning);
  font-size: 12px;
  line-height: 1.6;
}
.limitations summary {
  cursor: pointer;
}
.limitations p {
  margin: 6px 0;
}
@media (max-width: 900px) {
  .reason {
    padding: 14px 0 0;
    border-top: 1px solid var(--border-subtle);
    border-left: 0;
  }
}
@media (max-width: 640px) {
  .reason-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
  .evidence-button {
    min-height: 40px;
  }
}
</style>
