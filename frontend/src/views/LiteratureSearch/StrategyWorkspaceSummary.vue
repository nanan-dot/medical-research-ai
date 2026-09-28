<script setup lang="ts">
import { computed } from "vue";
import type { SearchStrategyDraft, StrategyCount, StrategyValidation } from "../../types/searchStrategy";

const props = defineProps<{
  strategy: SearchStrategyDraft;
  validation: StrategyValidation | null;
  count: StrategyCount | null;
  actionLoading: boolean;
  actionError: string | null;
}>();

const emit = defineEmits<{
  refreshMesh: [];
  validate: [];
  refreshCount: [];
}>();

const verifiedMeshCount = computed(() => props.strategy.mesh_terms.filter((term) => term.verification_status === "verified").length);
const unavailableMeshCount = computed(() => props.strategy.mesh_terms.filter((term) => term.verification_status === "unavailable").length);
</script>

<template>
  <section
    class="strategy-summary"
    aria-labelledby="strategy-summary-title"
  >
    <header class="section-header">
      <div>
        <p class="eyebrow">已保存的策略草稿</p>
        <h2 id="strategy-summary-title">检索策略工作台</h2>
      </div>
      <span class="revision">修订版 {{ props.strategy.revision }}</span>
    </header>

    <section
      class="summary-section"
      aria-labelledby="question-title"
    >
      <h3 id="question-title">研究问题</h3>
      <p>{{ props.strategy.research_question }}</p>
    </section>

    <section
      class="summary-section"
      aria-labelledby="terms-title"
    >
      <div class="inline-heading">
        <h3 id="terms-title">术语与 NLM MeSH</h3>
        <button
          type="button"
          :disabled="props.actionLoading"
          @click="emit('refreshMesh')"
        >
          刷新 NLM MeSH
        </button>
      </div>
      <p class="meta">{{ props.strategy.terms.length }} 个检索术语 · {{ verifiedMeshCount }} 个已验证 MeSH</p>
      <p
        v-if="unavailableMeshCount"
        class="warning"
        role="status"
      >
        NLM MeSH 暂时不可用：{{ unavailableMeshCount }} 项待重新查询。
      </p>
      <ul
        v-if="props.strategy.terms.length"
        class="term-list"
      >
        <li
          v-for="term in props.strategy.terms"
          :key="term.id"
        >
          <strong>{{ term.text }}</strong>
          <span>{{ term.source }}{{ term.is_locked ? " · 已锁定" : "" }}</span>
        </li>
      </ul>
      <p
        v-else
        class="empty"
      >
        暂时没有可用检索术语。
      </p>
    </section>

    <section
      class="summary-section"
      aria-labelledby="query-title"
    >
      <div class="inline-heading">
        <h3 id="query-title">PubMed 检索式验证</h3>
        <button
          type="button"
          :disabled="props.actionLoading"
          @click="emit('validate')"
        >
          验证语法
        </button>
      </div>
      <p
        v-if="props.validation"
        :class="props.validation.blocking_errors.length ? 'error' : 'success'"
      >
        {{ props.validation.blocking_errors.length ? props.validation.blocking_errors[0].message : "语法、MeSH 与字段标签已验证" }}
      </p>
      <p
        v-else
        class="meta"
      >
        修改检索式后需要重新验证。
      </p>
    </section>

    <section
      class="ready-state"
      aria-labelledby="count-title"
    >
      <div>
        <h3 id="count-title">PubMed 当前匹配</h3>
        <p v-if="props.count">{{ props.count.count }} 篇 · 来自 PubMed</p>
        <p v-else-if="props.strategy.count_state === 'stale'">匹配数量需要刷新</p>
        <p v-else>暂未获取匹配数量</p>
      </div>
      <button
        type="button"
        :disabled="props.actionLoading"
        @click="emit('refreshCount')"
      >
        刷新数量
      </button>
    </section>

    <p
      v-if="props.actionError"
      class="error"
      role="alert"
    >
      {{ props.actionError }}
    </p>
  </section>
</template>

<style scoped>
.strategy-summary { display:grid; gap:16px; padding:20px; border:1px solid var(--border-subtle); border-radius:12px; background:var(--surface); }
.section-header,.inline-heading,.ready-state { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.section-header h2,.section-header p,.summary-section h3,.summary-section p,.ready-state h3,.ready-state p { margin:0; }
.eyebrow,.meta,.term-list span { color:var(--text-muted); font-size:.8rem; }.eyebrow { color:var(--color-primary); font-weight:700; }
.revision { padding:4px 8px; border:1px solid var(--border-subtle); border-radius:999px; color:var(--text-secondary); font-size:.78rem; }
.summary-section { display:grid; gap:8px; padding-top:16px; border-top:1px solid var(--border-subtle); }.summary-section h3,.ready-state h3 { color:var(--text-primary); font-size:1rem; }
button { min-height:36px; padding:6px 10px; border:1px solid var(--border-strong); border-radius:6px; background:var(--surface); color:var(--color-primary); font:inherit; font-weight:700; cursor:pointer; } button:disabled { opacity:.55; cursor:wait; } button:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px; }
.term-list { display:grid; gap:6px; margin:0; padding:0; list-style:none; }.term-list li { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:8px 10px; background:var(--surface-muted); }.term-list strong { overflow-wrap:anywhere; }.term-list span { text-align:right; }
.ready-state { padding:14px; background:var(--color-success-soft); }.success { color:var(--color-success); }.warning { color:var(--color-warning); }.error { color:var(--color-danger); }.empty { color:var(--text-muted); }
@media (max-width:640px) { .section-header,.inline-heading,.ready-state { align-items:flex-start; flex-direction:column; }.inline-heading button,.ready-state button { width:100%; }.term-list li { align-items:flex-start; flex-direction:column; }.term-list span { text-align:left; } }
</style>
