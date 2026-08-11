<script setup lang="ts">
import { shallowRef } from "vue";
import AbstractDisclosure from "../../components/literature/AbstractDisclosure.vue";
import FulltextAccess from "../../components/literature/FulltextAccess.vue";
import PubMedLink from "../../components/literature/PubMedLink.vue";
import { useRecommendations } from "../../composables/useRecommendations";
const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });

const query = shallowRef("");
const candidateCount = shallowRef(5);
const { result, loading, error, recommend } = useRecommendations();

async function submit() {
  if (!query.value.trim()) return;
  await recommend(query.value.trim(), candidateCount.value);
}
</script>

<template>
  <main class="recommendation-page">
    <header v-if="!props.embedded" class="recommendation-header">
      <div>
        <h1>推荐阅读</h1>
        <p class="lede">输入研究主题，按服务端返回的优先级审阅真实 PubMed 候选和推荐依据。</p>
      </div>
      <div class="boundary-note" role="note">
        <span class="boundary-dot" aria-hidden="true"></span>
        <span>来源：PubMed</span>
      </div>
    </header>

    <form class="query-panel" @submit.prevent="submit">
      <label for="recommendation-query">研究主题</label>
      <textarea
        id="recommendation-query"
        v-model="query"
        maxlength="1000"
        rows="3"
        placeholder="输入新的研究主题"
        required
      ></textarea>
      <div class="query-controls">
        <span class="field-hint">仅返回 PubMed 检索到且通过质量门槛的记录</span>
        <label class="count-control" for="candidate-count">候选篇数
          <select id="candidate-count" v-model.number="candidateCount">
            <option v-for="count in [3, 5, 8, 10]" :key="count" :value="count">{{ count }} 篇</option>
          </select>
        </label>
        <button type="submit" :disabled="loading || !query.trim()">{{ loading ? "检索与融合中…" : "开始推荐" }}</button>
      </div>
    </form>

    <p v-if="error" class="state-message error" role="alert">{{ error }}。请检查后端服务或稍后重试。</p>
    <div v-else-if="loading" class="loading-state" role="status" aria-live="polite">
      <span class="loading-line"></span><span class="loading-line short"></span>
      正在检索真实文献，尚未生成结果。
    </div>

    <section v-else-if="result" class="results-area" aria-live="polite">
      <div class="results-heading">
        <div><p class="section-number">3. 推荐结果</p><h2>{{ result.items.length }} 篇可核验文献</h2></div>
        <span class="status-label" :class="result.status">{{ result.status === "completed" ? "已完成" : "已完成 · 含提示" }}</span>
      </div>
      <div v-if="result.warnings.length" class="warning-box" role="status">
        <strong>检索提示</strong><span v-for="warning in result.warnings" :key="warning">{{ warning }}</span>
      </div>
      <div v-if="!result.items.length" class="empty-state">
        <h3>没有找到可核验文献</h3><p>扩大主题范围或补充已收录的英文术语后再试。系统不会用模型记忆补充论文。</p>
      </div>
      <ol v-else class="result-list">
        <li v-for="item in result.items" :key="item.citation.pmid" class="result-item">
          <div class="result-index">{{ String(result.items.indexOf(item) + 1).padStart(2, "0") }}</div>
          <article class="recommendation-entry">
            <div class="citation-column">
            <div class="citation-meta"><span>PMID {{ item.citation.pmid }}</span><span v-if="item.citation.year">{{ item.citation.year }}</span><span v-if="item.citation.journal">{{ item.citation.journal }}</span></div>
            <h3>{{ item.citation.title || "未提供题名" }}</h3>
            <p class="authors">{{ item.citation.authors.join(", ") || "作者信息未提供" }}</p>
            <AbstractDisclosure :abstract-text="item.citation.abstract" />
            <div class="reading-links">
              <PubMedLink :pmid="item.citation.pmid" />
              <FulltextAccess :item="null" />
            </div>
            <p class="source-note">来源：PubMed · {{ item.citation.verified_on || "核验日期未提供" }} · 元数据由服务器装配</p>
            </div>
            <aside class="reason"><span class="reason-label">推荐理由</span><p>{{ item.recommendation_reason }}</p><span class="reason-basis">依据：服务端返回的已核验元数据与摘要</span></aside>
          </article>
        </li>
      </ol>
    </section>

    <section v-else class="empty-start">
      <span class="empty-mark" aria-hidden="true">⌕</span>
      <h2>从一个研究问题开始</h2>
      <p>推荐理由只来自检索到的真实摘要。没有检索结果，就不会出现论文卡片。</p>
    </section>
  </main>
</template>

<style scoped>
.recommendation-page{max-width:1440px;margin:0 auto;padding:1.4rem 1.5rem 2.6rem;color:var(--text-primary);display:grid;gap:1rem}.recommendation-header{display:flex;justify-content:space-between;gap:2rem;align-items:flex-start;border-bottom:1px solid var(--border-subtle);padding-bottom:1rem}.recommendation-header h1{margin:0 0 .35rem;font-size:clamp(1.75rem,2.5vw,2rem);line-height:1.2}.lede{margin:0;color:var(--text-muted);font-size:.9rem}.boundary-note{display:flex;align-items:center;gap:.5rem;padding:.4rem .6rem;border:1px solid var(--border-subtle);border-radius:6px;background:var(--surface-muted);color:var(--text-secondary);font-size:.75rem}.boundary-dot{width:.45rem;height:.45rem;border-radius:50%;background:var(--color-primary)}.query-panel{display:grid;gap:.7rem;padding:1rem;background:var(--surface);border:1px solid var(--border-subtle);box-shadow:var(--shadow-card);border-radius:8px}.query-panel>label{font-weight:700}.query-panel textarea{width:100%;resize:vertical;padding:.7rem;border:1px solid var(--border-strong);border-radius:6px;color:var(--text-primary);font:inherit;line-height:1.5;box-sizing:border-box}.query-panel textarea:focus{outline:2px solid var(--color-primary);outline-offset:1px;border-color:var(--color-primary)}.query-controls{display:flex;gap:1rem;align-items:center}.field-hint{margin-right:auto;color:var(--text-muted);font-size:.8rem}.count-control{display:flex;gap:.5rem;align-items:center;color:var(--text-muted);font-size:.85rem}.count-control select{padding:.45rem;border:1px solid var(--border-strong);border-radius:6px;background:var(--surface);color:var(--text-primary)}button{padding:.6rem 1rem;border:0;border-radius:6px;background:var(--color-primary);color:#fff;font:inherit;font-weight:700;cursor:pointer}button:disabled{opacity:.55;cursor:not-allowed}.state-message,.warning-box{padding:.85rem 1rem;border-radius:8px}.state-message.error{background:var(--color-danger-soft);color:#991b1b}.loading-state,.empty-start,.empty-state{text-align:center;padding:3rem 1rem;color:var(--text-muted);border:1px dashed var(--border-strong);border-radius:8px}.loading-line{display:block;width:220px;height:10px;margin:0 auto .6rem;background:var(--surface-muted);border-radius:5px;animation:pulse 1.3s infinite}.loading-line.short{width:140px;margin-bottom:1rem}.results-area{display:grid;gap:1rem}.results-heading{display:flex;align-items:end;justify-content:space-between}.section-number{margin:0;color:var(--color-primary);font-size:.78rem;font-weight:750}.results-heading h2{margin:.25rem 0 0;font-size:1.2rem}.status-label{padding:.35rem .6rem;border-radius:6px;font-size:.75rem;font-weight:800}.status-label.completed{background:var(--color-success-soft);color:#166534}.status-label.completed_with_warnings{background:var(--color-warning-soft);color:#92400e}.warning-box{display:flex;gap:.8rem;flex-wrap:wrap;background:var(--color-warning-soft);color:#92400e;font-size:.85rem}.warning-box span{font-weight:600}.result-list{display:grid;gap:0;margin:0;padding:0;list-style:none;background:var(--surface);border:1px solid var(--border-subtle);border-radius:8px;overflow:hidden}.result-item{display:grid;grid-template-columns:2rem minmax(0,1fr);gap:.75rem;padding:1rem;border-bottom:1px solid var(--border-subtle)}.result-item:last-child{border-bottom:0}.result-index{color:#fff;background:var(--color-primary);align-self:start;border-radius:5px;padding:.25rem 0;text-align:center;font-size:.78rem;font-weight:800}.recommendation-entry{display:grid;grid-template-columns:minmax(0,1fr) 15rem;gap:1rem}.citation-meta{display:flex;gap:.8rem;flex-wrap:wrap;color:var(--text-muted);font-size:.72rem;font-weight:700}.result-item h3{margin:.45rem 0 .25rem;font-size:1rem;line-height:1.4}.authors{margin:0;color:var(--text-muted);font-size:.82rem}.reason{align-self:stretch;padding:.75rem .85rem;border-left:2px solid var(--color-primary);background:var(--color-primary-soft)}.reason-label{color:var(--color-primary);font-size:.72rem;font-weight:800}.reason p{margin:.35rem 0;line-height:1.55;font-size:.85rem}.reason-basis{color:var(--text-muted);font-size:.72rem}.source-note{margin:.8rem 0 0;color:var(--text-faint);font-size:.72rem}.empty-start h2,.empty-state h3{margin:.8rem 0 .35rem;color:var(--text-primary)}.empty-start p,.empty-state p{max-width:520px;margin:auto;line-height:1.6}.empty-mark{font:3rem Georgia,serif;color:var(--color-primary)}@keyframes pulse{50%{opacity:.45}}@media(max-width:720px){.recommendation-header{display:grid}.boundary-note{justify-self:start}.query-controls{align-items:stretch;flex-wrap:wrap}.field-hint{width:100%;order:3}.result-item{grid-template-columns:1fr}.result-index{width:2rem}.recommendation-entry{grid-template-columns:1fr}.results-heading{align-items:start;gap:1rem;flex-direction:column}}
</style>
