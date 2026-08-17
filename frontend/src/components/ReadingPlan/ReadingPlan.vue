<script setup lang="ts">
import { computed, shallowRef } from "vue";
import type { ReadingCategory, ReadingOrder, ReadingOrderItem } from "../../api/literatureSearch";

// 类别标签与展示文案：与后端 ReadingCategory Literal 一一对应。
const CATEGORY_META: Record<ReadingCategory, { label: string; groupLabel: string; description: string; tone: string }> = {
  review: { label: "高质量综述", groupLabel: "先建立证据全貌", description: "先读综述，建立研究领域与证据版图。", tone: "tone-review" },
  guideline: { label: "指南或共识", groupLabel: "再看临床决策依据", description: "用于了解已形成的临床建议与共识。", tone: "tone-guideline" },
  original_research: { label: "代表性原始研究", groupLabel: "核验一手研究", description: "用于回到原始研究，核验具体研究设计与结果。", tone: "tone-original" },
  frontier: { label: "近年前沿研究", groupLabel: "追踪近年进展", description: "以发表时间为线索补充最新进展，不等同于质量更高。", tone: "tone-frontier" },
  highly_relevant: { label: "高相关研究", groupLabel: "补充问题相关候选", description: "依据本次 PubMed 返回排序补充阅读。", tone: "tone-relevant" },
};
const CATEGORY_ORDER: ReadingCategory[] = ["review", "guideline", "original_research", "frontier", "highly_relevant"];

interface Props {
  order: ReadingOrder | null;
  loading: boolean;
  saving: boolean;
  restoreNotice?: string;
  // 生成/保存失败的展示信息；空字符串表示无错误。
  error: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  generate: [];
  save: [order: string[]];
}>();

// 所有非空分类组，按证据金字塔顺序排列，供顶部章节索引与单章节序列共用。
const readingGroups = computed(() => {
  if (!props.order) return [];
  return CATEGORY_ORDER
    .map((category) => ({ category, meta: CATEGORY_META[category], items: props.order!.items.filter((item) => item.category === category) }))
    .filter((group) => group.items.length > 0);
});

// 顶部章节索引：当前选中的分类；默认第一个有文章的分类。
const activeCategory = shallowRef<ReadingCategory | null>(null);
const activeGroup = computed(() => {
  const groups = readingGroups.value;
  if (groups.length === 0) return null;
  return groups.find((group) => group.category === activeCategory.value) ?? groups[0];
});
function selectCategory(category: ReadingCategory): void {
  activeCategory.value = category;
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

function featureLabel(feature: string): string {
  if (feature === "verified=true") return "PubMed 已核实";
  if (feature.startsWith("position=")) return `PubMed 返回第 ${Number(feature.slice(9)) + 1} 位`;
  if (feature.startsWith("year=")) return `发表年份：${feature.slice(5)}`;
  if (feature.startsWith("publication_type=")) return `文献类型：${feature.slice(17)}`;
  if (feature.startsWith("frontier=")) return "近年发表信号";
  return feature;
}

// 手动调整：priority 是全局顺序（1..n），order.items 按 priority 排序，
// 因此 priority-1 即全局下标；上移与前一位置交换、下移与后一位置交换。
function swap(index: number, target: number): void {
  if (!props.order) return;
  const pmids = props.order.items.map((item) => item.pmid);
  if (target < 0 || target >= pmids.length) return;
  [pmids[index], pmids[target]] = [pmids[target], pmids[index]];
  emit("save", pmids);
}
</script>

<template>
  <section
    class="reading-plan"
    aria-label="阅读计划内容"
  >
    <p
      v-if="error"
      class="plan-error"
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-if="saving"
      class="plan-saving"
    >
      正在保存人工顺序…
    </p>

    <p
      v-if="!loading && !order"
      class="plan-empty"
    >
      尚未生成阅读顺序。
      <button
        class="generate-button"
        type="button"
        @click="emit('generate')"
      >
        生成阅读顺序
      </button>
    </p>
    <p
      v-else-if="loading && !order"
      class="plan-empty"
    >
      正在生成阅读顺序…
    </p>

    <template v-if="order">
      <!-- 顶部工具条：章节索引 + 重新生成，随内部滚动固定 -->
      <div class="plan-toolbar">
        <nav
          class="plan-index"
          aria-label="阅读章节导航"
        >
          <button
            v-for="group in readingGroups"
            :key="group.category"
            type="button"
            class="plan-index-item"
            :class="{ active: activeGroup?.category === group.category }"
            :aria-current="activeGroup?.category === group.category ? 'true' : undefined"
            @click="selectCategory(group.category)"
          >
            {{ group.meta.groupLabel }}
            <small>{{ group.items.length }} 篇</small>
          </button>
        </nav>
        <button
          class="generate-button"
          type="button"
          :disabled="loading || saving"
          @click="emit('generate')"
        >
          {{ loading ? "生成中…" : "重新生成" }}
        </button>
      </div>

      <!-- 当前章节序列 -->
      <section
        v-if="activeGroup"
        class="plan-chapter"
        :aria-labelledby="`plan-chapter-${activeGroup.category}`"
      >
        <header class="chapter-header">
          <div>
            <h3 :id="`plan-chapter-${activeGroup.category}`">{{ activeGroup.meta.groupLabel }}</h3>
            <p>{{ activeGroup.meta.description }}</p>
          </div>
          <span
            class="category-badge"
            :class="categoryTone(activeGroup.category)"
          >{{ activeGroup.meta.label }}</span>
        </header>
        <ol class="plan-list">
          <li
            v-for="(item, idx) in activeGroup.items"
            :key="item.pmid"
            class="plan-item"
          >
            <span
              class="priority"
              aria-label="阅读顺序"
            >{{ item.priority }}</span>
            <div class="item-body">
              <h4 class="item-title">{{ itemTitle(item) }}</h4>
              <p class="item-meta">PMID {{ item.pmid }} · {{ yearLabel(item) }}</p>
              <p
                v-if="item.evidence_features.length"
                class="item-features"
                aria-label="推荐信号"
              >
                <span
                  v-for="feature in item.evidence_features"
                  :key="feature"
                  class="feature-chip"
                >{{ featureLabel(feature) }}</span>
              </p>
              <details class="reason-disclosure">
                <summary>查看推荐依据</summary>
                <p>{{ item.reason }}</p>
              </details>
            </div>
            <div class="item-actions">
              <button
                type="button"
                :disabled="idx === 0 || loading || saving"
                @click="swap(item.priority - 1, item.priority - 2)"
              >
                上移
              </button>
              <button
                type="button"
                :disabled="idx === activeGroup.items.length - 1 || loading || saving"
                @click="swap(item.priority - 1, item.priority)"
              >
                下移
              </button>
            </div>
          </li>
        </ol>
      </section>

      <footer class="plan-foot">
        <span class="order-source">{{ order.order_source === "manual" ? "排序来源：用户人工顺序" : "排序来源：算法规则" }}</span>
        <span class="generated-at">生成于 {{ new Date(order.generated_at).toLocaleString("zh-CN", { hour12: false }) }}</span>
      </footer>
    </template>
  </section>
</template>

<style scoped>
.reading-plan { display: grid; gap: 0.75rem; max-height: calc(100dvh - 18rem); min-height: 0; padding: 0.75rem 1rem 1rem; overflow-y: scroll; overscroll-behavior: contain; scrollbar-gutter: stable; }
.generate-button { flex: 0 0 auto; padding: 0.4rem 0.8rem; border-radius: 7px; font: inherit; font-weight: 700; cursor: pointer; border: 0; background: var(--color-primary); color: #fff; white-space: nowrap; }
.generate-button:disabled { opacity: 0.55; }
.plan-error { margin: 0; padding: 0.7rem; color: var(--color-danger); background: var(--color-danger-soft, #fdecec); border-radius: 8px; }
.plan-saving { margin: 0; color: var(--text-muted); font-size: 0.82rem; }
.plan-empty { margin: 0; padding: 1.4rem; border: 1px dashed var(--border-strong); border-radius: 8px; text-align: center; color: var(--text-muted); }
.plan-empty .generate-button { display: inline-block; margin-top: 0.6rem; }

/* 顶部工具条：章节索引 + 重新生成，随内部滚动固定 */
.plan-toolbar { position: sticky; z-index: 4; top: 0; display: flex; align-items: center; gap: 0.75rem; padding-top: 0.2rem; border-bottom: 1px solid var(--border-subtle, #dbe4f0); background: var(--surface, #fff); }
.plan-index { display: flex; gap: 0.25rem; flex: 1 1 auto; flex-wrap: wrap; }
.plan-index-item { display: inline-flex; align-items: baseline; gap: 0.4rem; padding: 0.6rem 0.9rem 0.55rem; border: 0; border-bottom: 3px solid transparent; background: transparent; color: var(--text-muted); font: inherit; font-weight: 700; cursor: pointer; white-space: nowrap; }
.plan-index-item small { color: var(--text-faint, #94a3b8); font-weight: 500; font-size: 0.72rem; }
.plan-index-item.active { color: var(--text-primary); border-color: var(--color-primary); }
.plan-index-item.active small { color: var(--color-primary); }

/* 单章节序列 */
.plan-chapter { display: grid; gap: 0.6rem; }
.chapter-header { display: flex; align-items: start; justify-content: space-between; gap: 0.8rem; padding: 0.15rem 0; }
.chapter-header h3, .chapter-header p { margin: 0; }
.chapter-header h3 { color: var(--text-primary); font-size: 1rem; }
.chapter-header p { margin-top: 0.2rem; color: var(--text-muted); font-size: 0.8rem; line-height: 1.45; }
.category-badge { flex-shrink: 0; border-radius: 99px; padding: 0.22rem 0.55rem; font-size: 0.72rem; font-weight: 800; white-space: nowrap; }
.tone-review { background: #e8f0fe; color: #1a56db; }
.tone-guideline { background: #e6f7f0; color: #0f7a4d; }
.tone-original { background: #fdf3e7; color: #b25e09; }
.tone-frontier { background: #ede9fe; color: #6d28d9; }
.tone-relevant { background: #f1f5f9; color: #475569; }

.plan-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
.plan-item { display: flex; gap: 0.7rem; align-items: flex-start; padding: 0.8rem; border: 1px solid var(--border-color, #e1e7ef); border-radius: 8px; background: var(--surface, #fff); }
.priority { flex-shrink: 0; display: grid; place-items: center; width: 1.8rem; height: 1.8rem; border-radius: 99px; background: var(--color-primary); color: #fff; font-weight: 800; font-size: 0.82rem; }
.item-body { flex: 1; min-width: 0; display: grid; gap: 0.35rem; }
.item-title { margin: 0; color: var(--text-primary); font-size: .96rem; line-height: 1.45; overflow-wrap: anywhere; }
.item-meta { margin: 0; color: var(--text-muted); font-size: 0.76rem; font-family: ui-monospace, "SF Mono", Consolas, monospace; }
.item-features { display: flex; gap: 0.3rem; flex-wrap: wrap; margin: 0; }
.feature-chip { border-radius: 999px; padding: .18rem .45rem; background: var(--surface-muted, #f8fafc); border: 1px solid var(--border-color, #d9e1ed); color: var(--text-secondary); font-size: .7rem; }
.reason-disclosure { color: var(--text-muted); font-size: .77rem; }
.reason-disclosure summary { width: fit-content; color: var(--color-primary); cursor: pointer; }
.reason-disclosure p { margin: .35rem 0 0; line-height: 1.55; overflow-wrap: anywhere; }
.item-actions { display: flex; flex-direction: column; gap: 0.3rem; flex-shrink: 0; }
.item-actions button { padding: 0.25rem 0.55rem; border: 1px solid var(--border-color, #d9e1ed); border-radius: 6px; background: var(--surface, #ffffff); color: var(--text-primary); font: inherit; font-size: 0.74rem; cursor: pointer; }
.item-actions button:disabled { opacity: 0.4; cursor: default; }
.plan-foot { display: flex; justify-content: space-between; gap: 0.6rem; flex-wrap: wrap; color: var(--text-faint, #94a3b8); font-size: 0.76rem; }
@media (max-width: 640px) { .plan-toolbar { align-items: start; flex-direction: column; }.plan-index { flex-wrap: nowrap; overflow-x: auto; }.plan-index-item { flex: 0 0 auto; } }
</style>
