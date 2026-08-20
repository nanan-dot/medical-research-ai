<script setup lang="ts">
import { ref } from "vue";
import { citationCheckApi, type CitationAuditItem, type CitationCheckResult } from "../../api/citationCheck";

const manuscript = ref("");
const result = ref<CitationCheckResult | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

async function submit() {
  if (!manuscript.value.trim()) return;
  loading.value = true;
  error.value = null;
  try {
    result.value = await citationCheckApi.check(manuscript.value);
  } catch (cause) {
    console.warn("引用核验请求失败", cause);
    error.value = cause instanceof Error ? cause.message : "核验请求失败";
  } finally {
    loading.value = false;
  }
}

const statusLabel = (item: CitationAuditItem): string => {
  if (item.verified) return "已核实";
  return item.notes.some((note) => note.includes("未找到")) ? "未找到" : "无法验证";
};
</script>

<template>
  <main class="citation-check">
    <header class="page-header">
      <p class="eyebrow">CITATION CHECK · LIVE</p>
      <h1 class="page-title">引用核验</h1>
      <p class="page-copy">粘贴手稿或引用列表，逐条核对 PMID 与 DOI 是否在 PubMed / CrossRef 中真实存在。无法验证的引用会明确标记，不会凭记忆补全。</p>
    </header>

    <form class="manuscript-form" @submit.prevent="submit">
      <label class="manuscript-label">
        手稿或引用列表
        <textarea v-model="manuscript" maxlength="50000" required placeholder="例如：近期研究（PMID: 39000401）表明……；另见 https://doi.org/10.1038/nmeth.2089"></textarea>
      </label>
      <button type="submit" :disabled="loading">
        {{ loading ? "核验中…" : "开始核验" }}
      </button>
    </form>
    <p v-if="error" class="request-error" role="alert">{{ error }}</p>

    <section v-if="result" class="audit-report" aria-label="引用审计报告">
      <div class="summary-bar" :class="{ 'has-unverified': result.summary.unverified > 0 }">
        <span>共 {{ result.summary.total }} 条引用</span>
        <span class="summary-ok">✅ 已核实 {{ result.summary.verified }}</span>
        <span v-if="result.summary.unverified > 0" class="summary-bad">❌ 未通过 {{ result.summary.unverified }}</span>
      </div>

      <p v-if="result.items.length === 0" class="no-references">未识别到 PMID 或 DOI 引用。</p>
      <ul v-else class="audit-list">
        <li v-for="item in result.items" :key="`${item.kind}-${item.identifier}`" class="audit-item" :class="item.verified ? 'verified' : 'unverified'">
          <span class="status-mark">{{ item.verified ? "✅" : "❌" }}</span>
          <div class="item-body">
            <div class="item-head">
              <code class="kind-tag">{{ item.kind }}</code>
              <code class="identifier">{{ item.identifier }}</code>
              <span class="status-label">{{ statusLabel(item) }}</span>
            </div>
            <p v-if="item.raw" class="raw-snippet">…{{ item.raw }}</p>
            <dl v-if="item.verified_by" class="meta-row">
              <div><dt>验证来源</dt><dd>{{ item.verified_by }}</dd></div>
              <div><dt>验证时间</dt><dd>{{ item.verified_on }}</dd></div>
              <div v-if="item.matched"><dt>匹配标识符</dt><dd>{{ item.matched }}</dd></div>
            </dl>
            <ul v-if="item.notes.length" class="note-list">
              <li v-for="note in item.notes" :key="note">{{ note }}</li>
            </ul>
          </div>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.citation-check { max-width: 1000px; margin: auto; padding: 2rem 1.4rem 3rem; display: grid; gap: 1rem; }
.eyebrow { margin: 0; color: var(--color-primary); font-weight: 800; letter-spacing: 0.12em; font-size: 0.72rem; }
.page-title { margin: 0.25rem 0; color: var(--text-primary); font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1.1; }
.page-copy { max-width: 720px; color: var(--text-muted); line-height: 1.6; }

.manuscript-form { display: grid; gap: 0.75rem; padding: 1rem; background: var(--surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); box-shadow: var(--shadow); }
.manuscript-label { display: grid; gap: 0.35rem; font-weight: 700; color: var(--text-primary); }
.manuscript-label textarea { min-height: 180px; padding: 0.75rem; border: 1px solid var(--border-strong); border-radius: 8px; font: inherit; line-height: 1.6; resize: vertical; }
.manuscript-form button { justify-self: start; padding: 0.7rem 1.2rem; border: 0; border-radius: 8px; background: var(--color-primary); color: #fff; font-weight: 750; }
.manuscript-form button:disabled { opacity: 0.6; }

.request-error { margin: 0; padding: 0.8rem; color: var(--color-danger); background: var(--color-danger-soft); border-radius: 10px; }

.audit-report { display: grid; gap: 0.8rem; }
.summary-bar { display: flex; flex-wrap: wrap; gap: 0.9rem; align-items: center; padding: 0.9rem 1rem; border-radius: var(--radius-md); background: var(--surface-muted); font-weight: 750; }
.summary-bar.has-unverified { border-left: 4px solid var(--color-danger); }
.summary-ok { color: var(--color-success); }
.summary-bad { color: var(--color-danger); }

.no-references { padding: 1.2rem; border: 1px dashed var(--border-strong); border-radius: var(--radius-md); color: var(--text-muted); }
.audit-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.7rem; }
.audit-item { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 0.8rem; padding: 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface); }
.audit-item.verified { border-left: 4px solid var(--color-success); }
.audit-item.unverified { border-left: 4px solid var(--color-danger); }
.status-mark { font-size: 1.2rem; }
.item-body { display: grid; gap: 0.5rem; min-width: 0; }
.item-head { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
.kind-tag { padding: 0.12rem 0.45rem; border-radius: 6px; background: var(--color-primary-soft); color: var(--color-primary); font-size: 0.72rem; font-weight: 800; }
.identifier { font-weight: 800; color: var(--text-primary); word-break: break-all; }
.status-label { margin-left: auto; font-size: 0.82rem; font-weight: 700; color: var(--text-muted); }
.raw-snippet { margin: 0; color: var(--text-faint); font-size: 0.82rem; white-space: pre-wrap; word-break: break-word; }
.meta-row { display: flex; flex-wrap: wrap; gap: 1rem; margin: 0; padding-top: 0.5rem; border-top: 1px solid var(--border-subtle); }
.meta-row div { display: grid; gap: 0.1rem; }
.meta-row dt { font-size: 0.72rem; color: var(--text-faint); }
.meta-row dd { margin: 0; font-size: 0.84rem; color: var(--text-primary); word-break: break-all; }
.note-list { margin: 0; padding-left: 1.1rem; color: var(--color-danger); font-size: 0.84rem; }
</style>
