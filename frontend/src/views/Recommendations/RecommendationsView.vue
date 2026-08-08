<script setup lang="ts">
import { ref } from "vue";
import { useRecommendations } from "../../composables/useRecommendations";

const query = ref("");
const candidateCount = ref(5);
const { result, loading, error, recommend } = useRecommendations();

async function submit() {
  if (!query.value.trim()) return;
  await recommend(query.value.trim(), candidateCount.value);
}
</script>

<template>
  <main class="recommendation-page">
    <header class="recommendation-header">
      <div>
        <p class="eyebrow">EVIDENCE-LED RECOMMENDATION</p>
        <h1>从真实文献开始，找到值得读的方向</h1>
        <p class="lede">输入研究主题。系统先检索 PubMed，再仅基于已验证摘要生成推荐理由。</p>
      </div>
      <div class="boundary-note" role="note">
        <span class="boundary-dot" aria-hidden="true"></span>
        <span>LIVE · PubMed</span>
      </div>
    </header>

    <form class="query-panel" @submit.prevent="submit">
      <label for="recommendation-query">研究主题</label>
      <textarea
        id="recommendation-query"
        v-model="query"
        maxlength="1000"
        rows="3"
        placeholder="例如：肺癌免疫治疗的近期综述"
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
        <div><p class="eyebrow">VERIFIED RESULTS</p><h2>{{ result.items.length }} 篇可核验文献</h2></div>
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
          <article>
            <div class="citation-meta"><span>PMID {{ item.citation.pmid }}</span><span v-if="item.citation.year">{{ item.citation.year }}</span><span v-if="item.citation.journal">{{ item.citation.journal }}</span></div>
            <h3>{{ item.citation.title || "未提供题名" }}</h3>
            <p class="authors">{{ item.citation.authors.join(", ") || "作者信息未提供" }}</p>
            <div class="reason"><span class="reason-label">推荐理由</span><p>{{ item.recommendation_reason }}</p></div>
            <p class="source-note">来源：PubMed · {{ item.citation.verified_on || "核验日期未提供" }} · 元数据由服务器装配</p>
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
.recommendation-page{max-width:1120px;margin:0 auto;padding:2.5rem 1.4rem 4rem;color:var(--text-primary);display:grid;gap:1.5rem}.recommendation-header{display:flex;justify-content:space-between;gap:2rem;align-items:flex-start;border-bottom:1px solid var(--border-subtle);padding-bottom:1.6rem}.eyebrow{margin:0;color:var(--color-primary);font-size:.7rem;font-weight:800;letter-spacing:.13em}.recommendation-header h1{max-width:670px;margin:.45rem 0 .7rem;font-size:clamp(2rem,4vw,3.4rem);line-height:1.08;letter-spacing:-.04em}.lede{max-width:610px;margin:0;color:var(--text-muted);font-size:1rem}.boundary-note{display:flex;align-items:center;gap:.5rem;padding:.5rem .75rem;border:1px solid #bbf7d0;border-radius:999px;background:#f0fdf4;color:#166534;font-size:.73rem;font-weight:800;white-space:nowrap}.boundary-dot{width:.45rem;height:.45rem;border-radius:50%;background:var(--color-success)}.query-panel{display:grid;gap:.7rem;padding:1.2rem;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow-card);border-radius:var(--radius)}.query-panel>label{font-weight:800}.query-panel textarea{width:100%;resize:vertical;padding:.85rem;border:1px solid var(--line-strong);border-radius:8px;color:var(--text-primary);font:inherit;line-height:1.5;box-sizing:border-box}.query-panel textarea:focus{outline:3px solid var(--color-primary-soft);border-color:var(--color-primary)}.query-controls{display:flex;gap:1rem;align-items:center}.field-hint{margin-right:auto;color:var(--text-muted);font-size:.8rem}.count-control{display:flex;gap:.5rem;align-items:center;color:var(--text-muted);font-size:.85rem}.count-control select{padding:.55rem;border:1px solid var(--line-strong);border-radius:7px;background:var(--surface);color:var(--text-primary)}button{padding:.7rem 1.1rem;border:0;border-radius:8px;background:var(--color-primary);color:#fff;font:inherit;font-weight:800;cursor:pointer}button:disabled{opacity:.55;cursor:not-allowed}.state-message,.warning-box{padding:.85rem 1rem;border-radius:8px}.state-message.error{background:var(--color-danger-soft);color:#991b1b}.loading-state,.empty-start,.empty-state{text-align:center;padding:3rem 1rem;color:var(--text-muted);border:1px dashed var(--line-strong);border-radius:var(--radius)}.loading-line{display:block;width:220px;height:10px;margin:0 auto .6rem;background:var(--surface-muted);border-radius:5px;animation:pulse 1.3s infinite}.loading-line.short{width:140px;margin-bottom:1rem}.results-area{display:grid;gap:1rem}.results-heading{display:flex;align-items:end;justify-content:space-between}.results-heading h2{margin:.35rem 0 0;font-size:1.7rem}.status-label{padding:.35rem .6rem;border-radius:999px;font-size:.75rem;font-weight:800}.status-label.completed{background:var(--color-success-soft);color:#166534}.status-label.completed_with_warnings{background:var(--color-warning-soft);color:#92400e}.warning-box{display:flex;gap:.8rem;flex-wrap:wrap;background:var(--color-warning-soft);color:#92400e;font-size:.85rem}.warning-box span{font-weight:600}.result-list{display:grid;gap:0;margin:0;padding:0;list-style:none;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}.result-item{display:grid;grid-template-columns:56px 1fr;gap:1rem;padding:1.25rem 1.4rem;border-bottom:1px solid var(--line)}.result-item:last-child{border-bottom:0}.result-index{color:var(--text-faint);font:700 1.2rem/1.2 Georgia,serif}.citation-meta{display:flex;gap:.8rem;flex-wrap:wrap;color:var(--text-muted);font-size:.72rem;font-weight:700}.result-item h3{margin:.45rem 0 .25rem;font-size:1.15rem;line-height:1.4}.authors{margin:0;color:var(--text-muted);font-size:.82rem}.reason{margin-top:1rem;padding:.85rem 1rem;border-left:3px solid var(--color-secondary);background:#f0f9ff}.reason-label{color:#0369a1;font-size:.72rem;font-weight:800;letter-spacing:.08em}.reason p{margin:.35rem 0 0;line-height:1.55}.source-note{margin:.8rem 0 0;color:var(--text-faint);font-size:.72rem}.empty-start h2,.empty-state h3{margin:.8rem 0 .35rem;color:var(--text-primary)}.empty-start p,.empty-state p{max-width:520px;margin:auto;line-height:1.6}.empty-mark{font:3rem Georgia,serif;color:var(--color-primary)}@keyframes pulse{50%{opacity:.45}}@media(max-width:720px){.recommendation-header{display:grid}.boundary-note{justify-self:start}.query-controls{align-items:stretch;flex-wrap:wrap}.field-hint{width:100%;order:3}.result-item{grid-template-columns:1fr}.result-index{font-size:.8rem}.results-heading{align-items:start;gap:1rem;flex-direction:column}}
</style>
