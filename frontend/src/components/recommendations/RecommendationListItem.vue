<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import type {
  DismissReason,
  RecommendationItem,
} from "../../api/recommendations";
import RecommendationReasonPanel from "./RecommendationReasonPanel.vue";

const props = defineProps<{ item: RecommendationItem }>();
const emit = defineEmits<{
  accept: [RecommendationItem];
  dismiss: [RecommendationItem, DismissReason, HTMLElement | null];
  explanation: [RecommendationItem, HTMLElement | null];
}>();
const abstractOpen = ref(false);
const menuOpen = ref(false);
const menuRoot = ref<HTMLElement | null>(null);
function requestDismiss(event: MouseEvent): void {
  menuOpen.value = false;
  emit("dismiss", props.item, "off_topic", event.currentTarget as HTMLElement);
}
function closeMenuOnOutsidePress(event: MouseEvent): void {
  if (menuOpen.value && !menuRoot.value?.contains(event.target as Node))
    menuOpen.value = false;
}
function closeMenuOnEscape(event: KeyboardEvent): void {
  if (event.key === "Escape") menuOpen.value = false;
}
onMounted(() => {
  document.addEventListener("click", closeMenuOnOutsidePress);
  document.addEventListener("keydown", closeMenuOnEscape);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", closeMenuOnOutsidePress);
  document.removeEventListener("keydown", closeMenuOnEscape);
});
</script>

<template>
  <li class="item">
    <article class="paper">
      <span class="rank" :aria-label="`第 ${item.rank} 篇`">{{
        String(item.rank).padStart(2, "0")
      }}</span>
      <div class="paper-main">
        <div class="meta">
          <span>{{ item.citation.year || "年份暂缺" }}</span>
          <span class="journal">{{ item.citation.journal || "期刊暂缺" }}</span>
          <span class="publication-type">{{
            item.citation.publication_types.slice(0, 2).join(" · ")
          }}</span>
          <span class="candidate">{{
            item.overlap_status === "novel" ? "新增候选" : "已在当前结果"
          }}</span>
        </div>
        <h3 class="paper-title">{{ item.citation.title || "题名暂不可用" }}</h3>
        <p class="authors">
          {{
            item.citation.authors.length
              ? item.citation.authors.join(", ")
              : "作者暂缺"
          }}
          <span class="pmid">· PMID {{ item.pmid }}</span>
        </p>
        <div class="actions">
          <button
            type="button"
            :disabled="!item.citation.abstract"
            :aria-expanded="abstractOpen"
            :aria-controls="`abstract-${item.pmid}`"
            @click="abstractOpen = !abstractOpen"
          >
            {{
              abstractOpen
                ? "收起摘要"
                : item.citation.abstract
                  ? "查看摘要"
                  : "摘要不可用"
            }}
          </button>
          <a
            :href="`https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(item.pmid)}/`"
            target="_blank"
            rel="noopener noreferrer"
            >PubMed <span aria-hidden="true">↗</span></a
          >
          <div ref="menuRoot" class="more">
            <button
              type="button"
              aria-label="更多推荐操作"
              :aria-expanded="menuOpen"
              :aria-controls="`recommendation-menu-${item.pmid}`"
              @click="menuOpen = !menuOpen"
            >
              更多
            </button>
            <div
              v-if="menuOpen"
              :id="`recommendation-menu-${item.pmid}`"
              class="menu"
            >
              <button type="button" @click="requestDismiss">忽略此推荐</button>
            </div>
          </div>
          <button
            class="accept"
            type="button"
            :disabled="item.decision.decision !== 'pending'"
            @click="emit('accept', item)"
          >
            {{
              item.decision.decision === "accepted"
                ? "已加入候选"
                : item.decision.decision === "dismissed"
                  ? "已忽略"
                  : "加入候选"
            }}
          </button>
        </div>
        <div v-if="abstractOpen" :id="`abstract-${item.pmid}`" class="abstract">
          {{ item.citation.abstract }}
        </div>
      </div>
      <RecommendationReasonPanel
        :reason="item.reason"
        @explanation="emit('explanation', item, $event)"
      />
    </article>
  </li>
</template>

<style scoped>
.item {
  padding: 0;
  border-bottom: 1px solid var(--border-subtle);
  box-sizing: border-box;
}
.item:last-child {
  border-bottom: 0;
}
.paper {
  display: grid;
  grid-template-columns: 32px minmax(0, 3fr) minmax(340px, 2fr);
  column-gap: 16px;
  padding: 18px 16px;
}
.rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 5px;
  background: var(--color-primary);
  color: #fff;
  font: 700 12px/1 monospace;
}
.paper-main {
  min-width: 0;
  padding-right: 8px;
}
.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}
.journal {
  color: var(--text-primary);
}
.publication-type {
  font-size: 11px;
}
.candidate {
  color: var(--color-success);
  font-size: 11px;
}
.paper-title {
  margin: 7px 0 5px;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
.authors {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pmid {
  font-size: 11px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 12px;
}
.actions button,
.actions a {
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-size: 12px;
  text-decoration: none;
  cursor: pointer;
  padding: 5px 0;
}
.actions button:disabled {
  color: var(--text-muted);
  cursor: default;
}
.actions .accept {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  color: var(--text-primary);
  background: var(--surface);
}
.actions .accept:hover:enabled {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.more {
  position: relative;
}
.menu {
  position: absolute;
  z-index: 20;
  left: 0;
  bottom: 32px;
  min-width: 120px;
  padding: 8px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--surface);
  box-shadow: var(--shadow-card);
}
.menu button {
  color: var(--color-danger);
}
.abstract {
  margin-top: 14px;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.8;
}
.actions button:focus-visible,
.actions a:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}
@media (max-width: 900px) {
  .paper {
    grid-template-columns: 32px minmax(0, 1fr);
  }
  .paper > .reason {
    grid-column: 2;
    margin-top: 14px;
  }
  .paper-main {
    padding-right: 0;
  }
}
@media (max-width: 640px) {
  .paper {
    grid-template-columns: 1fr;
    padding: 16px 14px;
    gap: 4px;
  }
  .rank {
    display: none;
  }
  .paper > .reason {
    grid-column: 1;
  }
  .paper-title {
    font-size: 16px;
  }
  .actions {
    gap: 16px;
    flex-wrap: wrap;
  }
  .actions button,
  .actions a {
    min-height: 40px;
  }
  .authors {
    white-space: normal;
  }
  .publication-type {
    width: 100%;
  }
}
</style>
