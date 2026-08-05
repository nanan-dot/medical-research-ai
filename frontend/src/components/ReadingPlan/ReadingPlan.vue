<script setup lang="ts">
import type { ReadingCategory, ReadingOrder, ReadingOrderItem } from "../../api/literatureSearch";

// 类别标签与展示文案：与后端 ReadingCategory Literal 一一对应。
const CATEGORY_META: Record<ReadingCategory, { label: string; tone: string }> = {
  review: { label: "高质量综述", tone: "tone-review" },
  guideline: { label: "指南或共识", tone: "tone-guideline" },
  original_research: { label: "代表性原始研究", tone: "tone-original" },
  frontier: { label: "近年前沿研究", tone: "tone-frontier" },
  highly_relevant: { label: "高相关研究", tone: "tone-relevant" },
};

interface Props {
  order: ReadingOrder | null;
  loading: boolean;
  saving: boolean;
  // 生成/保存失败的展示信息；空字符串表示无错误。
  error: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  generate: [];
  save: [order: string[]];
}>();

function categoryLabel(category: ReadingCategory): string {
  return CATEGORY_META[category]?.label ?? category;
}

function categoryTone(category: ReadingCategory): string {
  return CATEGORY_META[category]?.tone ?? "tone-relevant";
}

function itemTitle(item: ReadingOrderItem): string {
  return item.title ?? "标题未提供";
}

function yearLabel(item: ReadingOrderItem): string {
  return item.year === null ? "年份未知" : `${item.year}`;
}

// 手动调整：把 index 处的条目与相邻条目交换位置，形成新的完整 PMID 顺序。
function swap(index: number, target: number): void {
  if (!props.order) return;
  const pmids = props.order.items.map((item) => item.pmid);
  if (target < 0 || target >= pmids.length) return;
  [pmids[index], pmids[target]] = [pmids[target], pmids[index]];
  emit("save", pmids);
}
</script>

<template>
  <section class="reading-plan" aria-labelledby="reading-plan-title">
    <header class="plan-header">
      <div>
        <p class="plan-kicker">READING ORDER · R2-WP08</p>
        <h2 id="reading-plan-title" class="plan-title">推荐阅读顺序</h2>
      </div>
      <button class="generate-button" :disabled="loading || saving" @click="emit('generate')">
        {{ loading ? "生成中…" : "生成阅读顺序" }}
      </button>
    </header>

    <p class="plan-copy">按证据金字塔层级推荐：综述 → 指南/共识 → 原始研究 → 近年前沿 → 高相关。可手动调整顺序并保存；重新生成不会覆盖人工顺序。</p>
    <p v-if="error" class="plan-error" role="alert">{{ error }}</p>
    <p v-if="saving" class="plan-saving">正在保存人工顺序…</p>

    <p v-if="!loading && !order" class="plan-empty">尚未生成阅读顺序。点击“生成阅读顺序”基于真实文献类型、年份与相关度信号生成可解释推荐。</p>
    <p v-else-if="loading && !order" class="plan-empty">正在生成阅读顺序…</p>

    <ol v-if="order" class="plan-list">
      <li v-for="(item, index) in order?.items ?? []" :key="item.pmid" class="plan-item">
        <span class="priority" aria-label="阅读顺序">{{ item.priority }}</span>
        <div class="item-body">
          <div class="item-head">
            <h3 class="item-title">{{ itemTitle(item) }}</h3>
            <span class="category-badge" :class="categoryTone(item.category)">{{ categoryLabel(item.category) }}</span>
          </div>
          <p class="item-meta">PMID {{ item.pmid }} · {{ yearLabel(item) }}</p>
          <p class="item-reason">{{ item.reason }}</p>
          <p v-if="item.evidence_features.length" class="item-features">
            <span v-for="feature in item.evidence_features" :key="feature" class="feature-chip">{{ feature }}</span>
          </p>
        </div>
        <div class="item-actions">
          <button :disabled="index === 0 || loading || saving" title="上移" aria-label="上移" @click="swap(index, index - 1)">↑</button>
          <button :disabled="index >= (order?.items.length ?? 0) - 1 || loading || saving" title="下移" aria-label="下移" @click="swap(index, index + 1)">↓</button>
        </div>
      </li>
    </ol>

    <footer v-if="order" class="plan-foot">
      <span class="order-source">{{ order.order_source === "manual" ? "排序来源：用户人工顺序" : "排序来源：算法规则" }}</span>
      <span class="generated-at">生成于 {{ new Date(order.generated_at).toLocaleString("zh-CN", { hour12: false }) }}</span>
    </footer>
  </section>
</template>

<style scoped>
.reading-plan { display: grid; gap: 0.75rem; padding: 1rem; border: 1px solid var(--border-color, #d9e1ed); border-radius: 12px; }
.plan-header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }
.plan-kicker { margin: 0; color: var(--text-muted); font-size: 0.78rem; letter-spacing: 0.1em; }
.plan-title { margin: 0.2rem 0 0; color: var(--text-primary); }
.generate-button { padding: 0.45rem 0.85rem; border: 0; border-radius: 7px; background: var(--color-primary); color: #fff; font-weight: 700; cursor: pointer; }
.generate-button:disabled { opacity: 0.55; }
.plan-copy { margin: 0; color: var(--text-muted); font-size: 0.84rem; line-height: 1.6; }
.plan-error { margin: 0; padding: 0.7rem; color: var(--color-danger); background: var(--color-danger-soft, #fdecec); border-radius: 8px; }
.plan-saving { margin: 0; color: var(--text-muted); font-size: 0.82rem; }
.plan-empty { margin: 0; padding: 1.4rem; border: 1px dashed var(--border-strong); border-radius: 8px; text-align: center; color: var(--text-muted); }
.plan-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
.plan-item { display: flex; gap: 0.7rem; align-items: flex-start; padding: 0.8rem; border: 1px solid var(--border-color, #e1e7ef); border-radius: 8px; background: var(--surface-muted, #f8fafc); }
.priority { flex-shrink: 0; display: grid; place-items: center; width: 1.8rem; height: 1.8rem; border-radius: 99px; background: var(--color-primary); color: #fff; font-weight: 800; font-size: 0.82rem; }
.item-body { flex: 1; min-width: 0; display: grid; gap: 0.35rem; }
.item-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.6rem; }
.item-title { margin: 0; color: var(--text-primary); font-size: 0.98rem; line-height: 1.4; overflow-wrap: anywhere; }
.category-badge { flex-shrink: 0; border-radius: 99px; padding: 0.22rem 0.55rem; font-size: 0.72rem; font-weight: 800; white-space: nowrap; }
.tone-review { background: #e8f0fe; color: #1a56db; }
.tone-guideline { background: #e6f7f0; color: #0f7a4d; }
.tone-original { background: #fdf3e7; color: #b25e09; }
.tone-frontier { background: #ede9fe; color: #6d28d9; }
.tone-relevant { background: #f1f5f9; color: #475569; }
.item-meta { margin: 0; color: var(--text-muted); font-size: 0.76rem; font-family: ui-monospace, "SF Mono", Consolas, monospace; }
.item-reason { margin: 0; color: var(--text-primary); font-size: 0.8rem; line-height: 1.6; overflow-wrap: anywhere; }
.item-features { display: flex; gap: 0.3rem; flex-wrap: wrap; margin: 0; }
.feature-chip { border-radius: 6px; padding: 0.15rem 0.4rem; background: var(--surface, #ffffff); border: 1px solid var(--border-color, #d9e1ed); color: var(--text-muted); font-size: 0.7rem; font-family: ui-monospace, "SF Mono", Consolas, monospace; }
.item-actions { display: flex; flex-direction: column; gap: 0.3rem; flex-shrink: 0; }
.item-actions button { width: 1.7rem; height: 1.7rem; border: 1px solid var(--border-color, #d9e1ed); border-radius: 6px; background: var(--surface, #ffffff); color: var(--text-primary); cursor: pointer; }
.item-actions button:disabled { opacity: 0.4; cursor: default; }
.plan-foot { display: flex; justify-content: space-between; gap: 0.6rem; flex-wrap: wrap; color: var(--text-faint, #94a3b8); font-size: 0.76rem; }
</style>
