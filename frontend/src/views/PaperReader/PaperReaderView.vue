<script setup lang="ts">
import { computed, nextTick, shallowRef, useTemplateRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { paperReaderApi } from "../../api/paperReader";
import type { ReaderRecord } from "../../api/paperReader";
import PaperReaderHeader from "../../components/paper-reader/PaperReaderHeader.vue";
import ReaderContextPanel from "../../components/paper-reader/ReaderContextPanel.vue";
import ReaderLeftRail from "../../components/paper-reader/ReaderLeftRail.vue";
import ReaderToolbar from "../../components/paper-reader/ReaderToolbar.vue";
import PdfReadingCanvas from "../../components/paper-reader/PdfReadingCanvas.vue";
import TranslatedReadingCanvas from "../../components/paper-reader/TranslatedReadingCanvas.vue";
import StatePanel from "../../components/ui/StatePanel.vue";
import { usePaperReaderBootstrap } from "../../composables/usePaperReaderBootstrap";
import type { PdfTextSelection } from "../../types/documentAnnotations";

const route = useRoute();
const router = useRouter();
const paperItemId = computed(() => {
  const value = Number(route.params.paperItemId);
  return Number.isInteger(value) && value > 0 ? value : null;
});
const researchContextId = computed(() => {
  const value = Number(route.query.research_context_id);
  return Number.isInteger(value) && value > 0 ? value : null;
});
const { bootstrap, loading, error, load } =
  usePaperReaderBootstrap(paperItemId);
const leftCollapsed = shallowRef(false);
const focusMode = shallowRef(false);
const favoriteBusy = shallowRef(false);
const actionError = shallowRef<string | null>(null);
const mobileRailOpen = shallowRef(false);
const currentPage = shallowRef(1);
const currentSelection = shallowRef<PdfTextSelection | null>(null);
watch(
  bootstrap,
  (value) => {
    if (value) currentPage.value = value.resume.page;
  },
  { immediate: true },
);
const readingCanvas =
  useTemplateRef<InstanceType<typeof PdfReadingCanvas>>("readingCanvas");
const contextPanel =
  useTemplateRef<InstanceType<typeof ReaderContextPanel>>("contextPanel");
async function toggleFavorite(): Promise<void> {
  if (!bootstrap.value) return;
  favoriteBusy.value = true;
  actionError.value = null;
  const previous = bootstrap.value.paper.is_favorite;
  bootstrap.value = {
    ...bootstrap.value,
    paper: { ...bootstrap.value.paper, is_favorite: !previous },
  };
  try {
    const result = await paperReaderApi.favorite(
      bootstrap.value.paper.paper_item_id,
      !previous,
      bootstrap.value.paper.favorite_version ?? 1,
    );
    bootstrap.value = {
      ...bootstrap.value,
        paper: { ...bootstrap.value.paper, is_favorite: result.is_favorite },
      };
    bootstrap.value = {
      ...bootstrap.value,
      paper: { ...bootstrap.value.paper, favorite_version: result.version },
    };
  } catch (cause) {
    bootstrap.value = {
      ...bootstrap.value,
      paper: { ...bootstrap.value.paper, is_favorite: previous },
    };
    actionError.value =
      cause instanceof Error ? cause.message : "收藏状态保存失败";
  } finally {
    favoriteBusy.value = false;
  }
}
async function startStudy(): Promise<void> {
  if (!bootstrap.value || !researchContextId.value) return;
  try {
    const handoff = await paperReaderApi.studyWorkspace(
      bootstrap.value.paper.paper_item_id,
      researchContextId.value,
    );
    await router.push(handoff.destination);
  } catch (cause) {
    actionError.value =
      cause instanceof Error ? cause.message : "无法创建研读工作区";
  }
}
async function setMode(
  mode: "original" | "bilingual" | "translated",
): Promise<void> {
  if (!bootstrap.value || bootstrap.value.capabilities.translation !== "available" && mode !== "original") return;
  try {
    await paperReaderApi.preference(
      bootstrap.value.paper.paper_item_id,
      bootstrap.value.paper.document_id,
      { view_mode: mode, expected_version: bootstrap.value.preference.version },
    );
    bootstrap.value = {
      ...bootstrap.value,
      preference: {
        ...bootstrap.value.preference,
        view_mode: mode,
        version: bootstrap.value.preference.version + 1,
      },
    };
  } catch (cause) {
    actionError.value =
      cause instanceof Error ? cause.message : "阅读偏好保存失败";
  }
}
async function showOriginalAnchor(anchorId: number): Promise<void> {
  await setMode("original");
  if (bootstrap.value?.preference.view_mode === "original") {
    await nextTick();
    await readingCanvas.value?.locateSourceAnchor(anchorId);
  }
}
async function goToPage(page: number): Promise<void> {
  if (!bootstrap.value) return;
  const next = Math.min(
    Math.max(1, Math.trunc(page)),
    bootstrap.value.document.page_count,
  );
  currentPage.value = next;
  await readingCanvas.value?.goToPage(next);
}
async function locateRecord(record: ReaderRecord): Promise<void> {
  if (record.page_number) await goToPage(record.page_number);
  if (record.source_anchor_id) await readingCanvas.value?.locateSourceAnchor(record.source_anchor_id);
}
async function fullscreen(): Promise<void> {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch (cause) {
    actionError.value =
      cause instanceof Error ? cause.message : "浏览器不支持全屏阅读";
  }
}
</script>
<template>
  <main class="reader-page">
    <StatePanel
      v-if="!paperItemId"
      title="请选择一篇论文"
      description="请从论文库打开一篇已关联 PDF 的论文，进入新的论文阅读工作区。"
      ><RouterLink to="/papers">返回论文库</RouterLink></StatePanel
    ><StatePanel
      v-else-if="loading"
      title="正在启动论文阅读"
      description="正在读取同一版本代际的论文、进度和阅读偏好。"
    /><StatePanel
      v-else-if="error"
      title="阅读工作区不可用"
      :description="error"
      ><button type="button" @click="load">重试</button></StatePanel
    ><template v-else-if="bootstrap"
      ><PaperReaderHeader
        :bootstrap="bootstrap"
        :favorite-busy="favoriteBusy"
        :study-enabled="Boolean(researchContextId)"
        @back="router.push('/papers')"
        @favorite="toggleFavorite"
        @study="startStudy" />
      <p v-if="actionError" class="action-error" role="alert">
        {{ actionError }}
      </p>
      <button
        v-if="!focusMode"
        class="mobile-nav-toggle"
        type="button"
        @click="mobileRailOpen = !mobileRailOpen"
      >
        阅读导航
      </button>
      <div
        class="reader-grid"
        :class="{
          focus: focusMode,
          leftcollapsed: leftCollapsed,
          'mobile-rail-open': mobileRailOpen,
        }"
      >
        <ReaderLeftRail
          :bootstrap="bootstrap"
          :collapsed="leftCollapsed"
          @toggle="leftCollapsed = !leftCollapsed"
          @page="goToPage"
        />
        <section
          class="reader-main"
          :aria-label="bootstrap.preference.view_mode === 'original' ? '论文原文阅读' : bootstrap.preference.view_mode === 'bilingual' ? '论文双语对照阅读' : '论文中文译文阅读'"
        >
          <ReaderToolbar
            :bootstrap="bootstrap"
            :focus-mode="focusMode"
            :current-page="currentPage"
            @mode="setMode"
            @focus="focusMode = !focusMode"
            @page="goToPage"
            @zoom="readingCanvas?.zoomBy($event)"
            @fullscreen="fullscreen"
          /><PdfReadingCanvas
            v-show="bootstrap.preference.view_mode === 'original'"
            ref="readingCanvas"
            :bootstrap="bootstrap"
            @records-changed="contextPanel?.refresh()"
            @selection-changed="currentSelection = $event"
            @translate-selection="contextPanel?.openTranslation()"
          />
          <TranslatedReadingCanvas
            v-if="bootstrap.preference.view_mode !== 'original'"
            :bootstrap="bootstrap"
            :current-page="currentPage"
            :mode="bootstrap.preference.view_mode"
            @locate-source-anchor="showOriginalAnchor"
          />
        </section>
        <ReaderContextPanel
          v-if="!focusMode"
          ref="contextPanel"
          :bootstrap="bootstrap"
          :selection="currentSelection"
          @locate="locateRecord"
          @locate-source-anchor="readingCanvas?.locateSourceAnchor($event)"
        /></div
    ></template>
  </main>
</template>
<style scoped>
.reader-page {
  --reader-blue: #0868f7;
  --reader-ink: #111827;
  --reader-muted: #667085;
  --reader-line: #e5eaf2;
  min-height: 100vh;
  overflow: hidden;
  background: #f7f9fc;
}
.action-error {
  margin: 0;
  padding: 8px 24px;
  background: #fff0f0;
  color: #b42318;
  font-size: 13px;
}
.reader-grid {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr) 455px;
  min-height: calc(100vh - 70px);
}
.reader-grid.leftcollapsed {
  grid-template-columns: 46px minmax(0, 1fr) 634px;
}
.reader-grid.focus {
  grid-template-columns: 46px minmax(0, 1fr);
}
.reader-main {
  min-width: 0;
  background: #fff;
}
.mobile-nav-toggle {
  display: none;
}
@media (max-width: 1279px) {
  .reader-grid {
    grid-template-columns: 224px minmax(0, 1fr) 390px;
  }
  .reader-grid.leftcollapsed {
    grid-template-columns: 46px minmax(0, 1fr) 524px;
  }
}
@media (max-width: 1023px) {
  .reader-grid,
  .reader-grid.leftcollapsed,
  .reader-grid.focus {
    grid-template-columns: 1fr;
  }
  .reader-grid :deep(.left-rail) {
    display: none;
  }
  .reader-grid.mobile-rail-open :deep(.left-rail) {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 8;
    display: grid;
    width: min(82vw, 310px);
    box-shadow: 0 12px 32px #0b1f3a33;
  }
  .mobile-nav-toggle {
    display: block;
    position: fixed;
    right: 14px;
    bottom: 14px;
    z-index: 9;
    padding: 10px 14px;
    border: 1px solid #1769e8;
    border-radius: 10px;
    background: #1769e8;
    color: white;
    font-weight: 700;
  }
  .reader-page :deep(.reader-header) {
    position: sticky;
    top: 0;
    z-index: 5;
  }
  .reader-page :deep(.context) {
    grid-row: 3;
  }
}
@media (max-width: 767px) {
  .reader-page { overflow: visible; }
}
</style>
