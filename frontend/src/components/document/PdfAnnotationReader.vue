<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  shallowRef,
  useTemplateRef,
  watch,
} from "vue";
import {
  getDocument,
  GlobalWorkerOptions,
  TextLayer,
  version as pdfjsVersion,
  type PDFDocumentLoadingTask,
  type PDFDocumentProxy,
} from "pdfjs-dist/legacy/build/pdf.mjs";
import workerSource from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?url";

import type { DocumentAnnotation } from "../../api/documentAnnotations";
import PdfPageShell from "./PdfPageShell.vue";
import type { PdfTextSelection } from "../../types/documentAnnotations";
import type { AnchorVersion } from "../../types/sourceAnchors";
import { sourceAnchorsApi } from "../../api/sourceAnchors";
import {
  bindTextLayer,
  captureMappedRange,
  type MappedText,
} from "../../utils/pdfSelection";
import { useAnchorHighlights } from "../../composables/useAnchorHighlights";
import { usePageRenderScheduler } from "../../composables/usePageRenderScheduler";
import { usePdfPageWindow } from "../../composables/usePdfPageWindow";
import { useVisibleSegments } from "../../composables/useVisibleSegments";
import type { VisibleReadingContext } from "../../types/readingContext";

GlobalWorkerOptions.workerSrc = workerSource;

const props = defineProps<{
  sourceUrl: string;
  annotations: readonly DocumentAnnotation[];
  selectedAnnotationId: number | null;
  documentId?: number;
  fileHash?: string;
  frozen?: boolean;
  selectionEpoch?: number;
}>();

const emit = defineEmits<{
  selectionChange: [selection: PdfTextSelection | null];
  selectAnnotation: [annotationId: number];
  readingContextChange: [context: VisibleReadingContext | null];
}>();

const readerElement = useTemplateRef<HTMLElement>("readerElement");
const pageNumbers = shallowRef<number[]>([]);
const loading = shallowRef(false);
const errorMessage = shallowRef<string | null>(null);
const selectionError = shallowRef<string | null>(null);
const selection = shallowRef<PdfTextSelection | null>(null);
const hasSelectableText = shallowRef(false);
const zoom = shallowRef(1.25);
const pageSizes = shallowRef<readonly { width: number; height: number }[]>([]);
const pageErrors = shallowRef<Record<number, string>>({});
const navigationPage = shallowRef<number | null>(null);
const pageInput = shallowRef(1);
const thumbnailPages = computed(() => {
  const total = pageNumbers.value.length;
  const start = Math.max(
    1,
    Math.min(pageInput.value - 3, Math.max(1, total - 6)),
  );
  return Array.from(
    { length: Math.min(7, total) },
    (_, index) => start + index,
  );
});
const renderedPages = new Set<number>();
const pendingPages = new Set<number>();
const renderingPages = new Map<number, number>();
let documentProxy: PDFDocumentProxy | null = null;
let loadingTask: PDFDocumentLoadingTask | null = null;
let renderVersion = 0;
let anchorVersion: AnchorVersion | null = null;
let mappings: MappedText[] = [];
const activeRenderTasks = new Map<number, { cancel: () => void }>();
const activeMappingRequests = new Map<number, AbortController>();
const {
  highlights: annotationRects,
  locationStatus,
  refresh: refreshHighlights,
  clear: clearHighlights,
} = useAnchorHighlights();
const pageScheduler = usePageRenderScheduler({
  concurrency: 1,
  render: async (pageNumber, generation) => {
    renderingPages.set(pageNumber, generation);
    try {
      if (
        documentProxy &&
        generation === renderVersion &&
        pageWindow.wants(pageNumber)
      ) {
        await renderPage(documentProxy, pageNumber, generation);
      }
    } finally {
      if (renderingPages.get(pageNumber) === generation)
        renderingPages.delete(pageNumber);
      if (generation === renderVersion) {
        pendingPages.delete(pageNumber);
        if (!pageWindow.wants(pageNumber)) releasePage(pageNumber);
      }
    }
  },
  onError: (cause, request) => {
    if (pageWindow.wants(request.pageNumber))
      pageErrors.value = {
        ...pageErrors.value,
        [request.pageNumber]:
          cause instanceof Error ? cause.message : "页面渲染失败",
      };
  },
});
const pageWindow = usePdfPageWindow({
  root: readerElement,
  pinnedPages: () => [
    ...(selection.value?.anchorDescriptor?.fragments.map(
      (fragment) => fragment.page_number,
    ) ?? []),
    ...(navigationPage.value ? [navigationPage.value] : []),
  ],
  onChange: (wanted, visible) => {
    pageScheduler.retainPages(wanted);
    for (const page of pageNumbers.value) {
      if (!wanted.has(page)) {
        if (!renderingPages.has(page)) pendingPages.delete(page);
        releasePage(page);
      } else if (
        !renderedPages.has(page) &&
        !pendingPages.has(page) &&
        !pageErrors.value[page]
      ) {
        pendingPages.add(page);
        pageScheduler.enqueue({
          pageNumber: page,
          generation: renderVersion,
          priority:
            page === navigationPage.value
              ? "navigation"
              : visible.has(page)
                ? "visible"
                : "buffer",
        });
      }
    }
  },
});
const visibleSegments = useVisibleSegments({
  root: readerElement,
  mappings: () => mappings,
  publish: (context) => emit("readingContextChange", context),
});

function refreshWindow(event?: Event): void {
  pageWindow.refresh();
  visibleSegments.schedule(event?.type === "focusin" ? "keyboard" : "scroll");
}

function releasePage(pageNumber: number): void {
  if (renderingPages.has(pageNumber)) return;
  const shell = readerElement.value?.querySelector<HTMLElement>(
    `.pdf-page[data-page-number="${pageNumber}"]`,
  );
  const canvas = shell?.querySelector("canvas");
  if (canvas) {
    canvas.width = 0;
    canvas.height = 0;
  }
  shell?.querySelector(".text-layer")?.replaceChildren();
  mappings = mappings.filter(
    (mapping) => mapping.metadata.page_number !== pageNumber,
  );
  renderedPages.delete(pageNumber);
  visibleSegments.release(pageNumber);
}

async function preparePageSizes(
  pdf: PDFDocumentProxy,
  generation: number,
): Promise<void> {
  const sizes: { width: number; height: number }[] = [];
  // 先读取轻量页尺寸，确保混合纸张及旋转页在回收后仍占据同样的位置。
  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    if (generation !== renderVersion) return;
    const viewport = page.getViewport({ scale: 1 });
    sizes.push({ width: viewport.width, height: viewport.height });
  }
  pageSizes.value = sizes;
}

async function navigatePage(): Promise<void> {
  if (
    !Number.isInteger(pageInput.value) ||
    pageInput.value < 1 ||
    pageInput.value > pageNumbers.value.length
  )
    return;
  navigationPage.value = pageInput.value;
  pageWindow.refresh();
  visibleSegments.schedule("navigation");
  readerElement.value
    ?.querySelector<HTMLElement>(
      `.pdf-page[data-page-number="${pageInput.value}"]`,
    )
    ?.scrollIntoView({ behavior: "auto", block: "start" });
  await nextTick();
  void renderThumbnails();
}

async function renderThumbnails(): Promise<void> {
  const pdf = documentProxy;
  if (!pdf) return;
  await Promise.all(
    thumbnailPages.value.map(async (pageNumber) => {
      const canvas = document.querySelector<HTMLCanvasElement>(
        `.pdf-reader .thumbnail[data-page-number="${pageNumber}"] canvas`,
      );
      if (!canvas || canvas.dataset.rendered === props.sourceUrl) return;
      const page = await pdf.getPage(pageNumber);
      const viewport = page.getViewport({ scale: 0.13 });
      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * pixelRatio);
      canvas.height = Math.floor(viewport.height * pixelRatio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      const context = canvas.getContext("2d");
      if (!context) return;
      await page.render({
        canvas,
        canvasContext: context,
        viewport,
        transform:
          pixelRatio === 1 ? undefined : [pixelRatio, 0, 0, pixelRatio, 0, 0],
      }).promise;
      canvas.dataset.rendered = props.sourceUrl;
    }),
  );
}

/** 复用 A2 锚点坐标回到 PDF 原文；找不到已渲染 TextItem 时只降级到页首。 */
async function locateSourceAnchor(anchorId: number): Promise<void> {
  if (!props.fileHash || !props.documentId) return;
  try {
    const anchor = await sourceAnchorsApi.get(anchorId);
    if (
      anchor.document_id !== props.documentId ||
      anchor.file_hash !== props.fileHash ||
      anchor.resolution_status !== "exact"
    ) {
      selectionError.value = "该译文的原文锚点已失效，无法精确定位。";
      return;
    }
    const fragment = anchor.fragments[0];
    if (!fragment) return;
    pageInput.value = fragment.page_number;
    await navigatePage();
    await pageScheduler.whenIdle();
    const mapping = mappings.find(
      (item) =>
        item.metadata.page_number === fragment.page_number &&
        item.item.item_index === fragment.start_item_index,
    );
    (
      mapping?.node.parentElement ??
      readerElement.value?.querySelector<HTMLElement>(
        `.pdf-page[data-page-number="${fragment.page_number}"]`,
      )
    )?.scrollIntoView({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
      block: "center",
    });
  } catch (cause) {
    selectionError.value =
      cause instanceof Error ? cause.message : "原文锚点读取失败，请重试定位。";
  }
}

function retryPage(pageNumber: number): void {
  const errors = { ...pageErrors.value };
  delete errors[pageNumber];
  pageErrors.value = errors;
  pageWindow.refresh();
}

function annotationRectsForPage(pageNumber: number) {
  return annotationRects.value.get(pageNumber) ?? [];
}

function selectionRectsForPage(pageNumber: number) {
  if (!selection.value) return [];
  if (selection.value.anchorDescriptor) {
    return selection.value.anchorDescriptor.fragments
      .filter((fragment) => fragment.page_number === pageNumber)
      .flatMap((fragment) => fragment.rectangles);
  }
  return selection.value.pageNumber === pageNumber
    ? selection.value.rectangles
    : [];
}

async function loadPdf(): Promise<void> {
  const currentRenderVersion = ++renderVersion;
  pageWindow.disconnect();
  visibleSegments.clear();
  cancelPageRenders();
  pageScheduler.invalidate(currentRenderVersion);
  loadingTask?.destroy();
  documentProxy = null;
  anchorVersion = null;
  mappings = [];
  renderedPages.clear();
  pendingPages.clear();
  pageErrors.value = {};
  navigationPage.value = null;
  pageInput.value = 1;
  pageSizes.value = [];
  clearHighlights();
  pageNumbers.value = [];
  hasSelectableText.value = false;
  clearSelection();
  loading.value = true;
  errorMessage.value = null;
  try {
    const task = getDocument({ url: props.sourceUrl });
    loadingTask = task;
    const pdf = await task.promise;
    if (currentRenderVersion !== renderVersion) return;
    documentProxy = pdf;
    if (props.documentId && props.fileHash) {
      try {
        const version = await sourceAnchorsApi.version(
          props.documentId,
          props.fileHash,
        );
        if (currentRenderVersion !== renderVersion) return;
        anchorVersion = version;
      } catch (cause) {
        if (currentRenderVersion !== renderVersion) return;
        selectionError.value =
          cause instanceof Error ? cause.message : "原文锚点层不可用";
      }
    }
    await preparePageSizes(pdf, currentRenderVersion);
    if (currentRenderVersion !== renderVersion) return;
    pageNumbers.value = Array.from(
      { length: pdf.numPages },
      (_, index) => index + 1,
    );
    await nextTick();
    // 缩略图在用户跳转页面时按需绘制，避免初始加载与正文页竞争渲染资源。
    if (currentRenderVersion !== renderVersion) return;
    if (readerElement.value) readerElement.value.scrollTop = 0;
    pageWindow.connect(pdf.numPages);
    await pageScheduler.whenIdle();
    if (currentRenderVersion === renderVersion)
      await refreshHighlights(props.annotations, mappings, props.fileHash);
  } catch (cause) {
    if (currentRenderVersion !== renderVersion) return;
    errorMessage.value =
      cause instanceof Error ? cause.message : "无法加载 PDF 原文";
  } finally {
    if (currentRenderVersion === renderVersion) loading.value = false;
  }
}

async function renderPage(
  pdf: PDFDocumentProxy,
  pageNumber: number,
  generation: number,
): Promise<void> {
  const page = await pdf.getPage(pageNumber);
  if (generation !== renderVersion) return;
  const viewport = page.getViewport({ scale: zoom.value });
  const pageElement = readerElement.value?.querySelector<HTMLElement>(
    `[data-page-number="${pageNumber}"]`,
  );
  const canvas = pageElement?.querySelector<HTMLCanvasElement>("canvas");
  const textLayerElement =
    pageElement?.querySelector<HTMLElement>(".text-layer");
  if (!pageElement || !canvas || !textLayerElement) return;

  const pixelRatio = window.devicePixelRatio || 1;
  pageElement.style.width = `${viewport.width}px`;
  pageElement.style.height = `${viewport.height}px`;
  canvas.width = Math.floor(viewport.width * pixelRatio);
  canvas.height = Math.floor(viewport.height * pixelRatio);
  canvas.style.width = `${viewport.width}px`;
  canvas.style.height = `${viewport.height}px`;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器不支持 PDF 渲染画布");
  const renderTask = page.render({
    canvas,
    canvasContext: context,
    viewport,
    transform: [pixelRatio, 0, 0, pixelRatio, 0, 0],
  });
  const cancellableTask = renderTask;
  activeRenderTasks.set(pageNumber, cancellableTask);
  try {
    await cancellableTask.promise;
  } finally {
    if (activeRenderTasks.get(pageNumber) === cancellableTask)
      activeRenderTasks.delete(pageNumber);
  }
  if (generation !== renderVersion) return;
  textLayerElement.replaceChildren();
  textLayerElement.style.setProperty("--scale-factor", String(viewport.scale));
  const content = await page.getTextContent({
    includeMarkedContent: true,
    disableNormalization: false,
  });
  if (generation !== renderVersion) return;
  const textLayer = new TextLayer({
    textContentSource: content,
    container: textLayerElement,
    viewport,
  });
  activeRenderTasks.set(pageNumber, textLayer);
  try {
    await textLayer.render();
  } finally {
    if (activeRenderTasks.get(pageNumber) === textLayer)
      activeRenderTasks.delete(pageNumber);
  }
  if (generation !== renderVersion) return;
  hasSelectableText.value =
    hasSelectableText.value || textLayerElement.querySelector("span") !== null;
  if (anchorVersion && props.documentId) {
    let mappingRequest: AbortController | null = null;
    try {
      // 页面离开窗口或代际变化时中止映射请求，不能让远页网络队列占用当前阅读。
      mappingRequest = new AbortController();
      activeMappingRequests.get(pageNumber)?.abort();
      activeMappingRequests.set(pageNumber, mappingRequest);
      const metadata = await sourceAnchorsApi.page(
        props.documentId,
        pageNumber,
        anchorVersion,
        mappingRequest.signal,
      );
      if (activeMappingRequests.get(pageNumber) === mappingRequest)
        activeMappingRequests.delete(pageNumber);
      if (generation !== renderVersion) return;
      if (
        metadata.pdfjs_version !== pdfjsVersion ||
        metadata.rotation !== viewport.rotation
      ) {
        throw new Error(
          "TEXT_LAYER_MAPPING_MISMATCH：PDF.js 版本或页面旋转不一致。",
        );
      }
      const indexes = content.items.flatMap((item, index) =>
        "str" in item ? [index] : [],
      );
      mappings.push(
        ...bindTextLayer(
          pageElement,
          textLayer.textDivs,
          textLayer.textContentItemsStr,
          indexes,
          metadata,
        ),
      );
    } catch (cause) {
      if (generation === renderVersion && !mappingRequest?.signal.aborted) {
        selectionError.value =
          cause instanceof Error ? cause.message : "文本映射失败";
      }
    } finally {
      if (
        mappingRequest &&
        activeMappingRequests.get(pageNumber) === mappingRequest
      )
        activeMappingRequests.delete(pageNumber);
    }
  }
  if (generation === renderVersion && pageWindow.wants(pageNumber)) {
    renderedPages.add(pageNumber);
    await refreshHighlights(props.annotations, mappings, props.fileHash);
    if (generation === renderVersion && anchorVersion && props.documentId) {
      await visibleSegments.loadPage(
        props.documentId,
        anchorVersion,
        pageNumber,
      );
    }
  }
}

async function changeZoom(delta: number): Promise<void> {
  const nextZoom = Math.min(2, Math.max(0.8, zoom.value + delta));
  if (nextZoom === zoom.value || !documentProxy) return;
  if (props.frozen) return;
  zoom.value = nextZoom;
  const generation = ++renderVersion;
  cancelPageRenders();
  pageScheduler.invalidate(generation);
  mappings = [];
  renderedPages.clear();
  pendingPages.clear();
  pageErrors.value = {};
  clearHighlights();
  visibleSegments.clear();
  clearSelection();
  loading.value = true;
  await nextTick();
  try {
    pageWindow.reconnect();
    await pageScheduler.whenIdle();
    if (generation === renderVersion)
      await refreshHighlights(props.annotations, mappings, props.fileHash);
  } finally {
    if (generation === renderVersion) loading.value = false;
  }
}

function captureSelection(clearWhenEmpty = false): void {
  // 页面窗口会在后台继续预取相邻页；已渲染且已映射的当前页不应
  // 因全局预取状态而失去选区能力。跨未完成页面的情况仍在下方拒绝。
  if (props.frozen) return;
  const browserSelection = window.getSelection();
  if (!browserSelection || browserSelection.rangeCount === 0) {
    if (clearWhenEmpty) clearSelection();
    return;
  }
  const selectedText = browserSelection
    .toString()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
  if (!selectedText) {
    if (clearWhenEmpty) clearSelection();
    return;
  }
  const startPage = pageElementForNode(browserSelection.anchorNode);
  const endPage = pageElementForNode(browserSelection.focusNode);
  if (!startPage && !endPage) return;
  if (!startPage || !endPage) {
    clearSelection();
    selectionError.value = "选区端点必须都位于当前 PDF。";
    return;
  }
  const firstPage = Math.min(
    Number(startPage.dataset.pageNumber),
    Number(endPage.dataset.pageNumber),
  );
  const lastPage = Math.max(
    Number(startPage.dataset.pageNumber),
    Number(endPage.dataset.pageNumber),
  );
  if (
    pageNumbers.value.some(
      (page) =>
        page >= firstPage && page <= lastPage && !renderedPages.has(page),
    )
  ) {
    // 保留浏览器 Range 以固定待加载页面，但撤销上一次可保存的草稿。
    clearSelection(false);
    pageWindow.refresh();
    selectionError.value = "跨页选区中的页面尚未加载完成，请稍后重新选择。";
    return;
  }
  if (!anchorVersion) {
    if (firstPage !== lastPage) {
      clearSelection(false);
      selectionError.value = "锚点处理中时，请先选择同一页内的文字。";
      return;
    }
    const pageBox = startPage.getBoundingClientRect();
    const rectangles = Array.from(
      browserSelection.getRangeAt(0).getClientRects(),
    )
      .filter((rect) => rect.width > 0 && rect.height > 0)
      .map((rect) => ({
        left: Math.max(0, (rect.left - pageBox.left) / pageBox.width),
        top: Math.max(0, (rect.top - pageBox.top) / pageBox.height),
        width: Math.min(1, rect.width / pageBox.width),
        height: Math.min(1, rect.height / pageBox.height),
      }));
    if (!rectangles.length) {
      selectionError.value = "未能读取选区位置，请重新选择文字。";
      return;
    }
    const nextSelection: PdfTextSelection = {
      pageNumber: firstPage,
      rectangles,
      selectedText,
    };
    selectionError.value = null;
    selection.value = nextSelection;
    emit("selectionChange", nextSelection);
    if (clearWhenEmpty) browserSelection.removeAllRanges();
    return;
  }
  try {
    const captured = captureMappedRange(
      browserSelection.getRangeAt(0),
      mappings,
    );
    const first = captured.fragments[0]!;
    const nextSelection: PdfTextSelection = {
      pageNumber: first.page_number,
      rectangles: first.rectangles,
      selectedText: captured.browserQuote,
      anchorDescriptor: {
        ...anchorVersion,
        browser_quote: captured.browserQuote,
        fragments: captured.fragments,
      },
    };
    selectionError.value = null;
    selection.value = nextSelection;
    emit("selectionChange", nextSelection);
    visibleSegments.schedule("selection");
    // Freeze the verified item rectangles into our overlay. Native browser
    // highlighting follows PDF.js DOM order and may paint an adjacent column.
    if (clearWhenEmpty) browserSelection.removeAllRanges();
  } catch (cause) {
    clearSelection(false);
    selectionError.value =
      cause instanceof Error ? cause.message : "选区无法精确映射";
  }
}

function handleSelectionChange(): void {
  // 浏览器在拖选过程中会多次触发该事件；延后到当前事件循环末尾可读取最终 Range。
  window.setTimeout(() => captureSelection(), 0);
}

function clearSelection(clearBrowserSelection = true): void {
  selection.value = null;
  selectionError.value = null;
  if (clearBrowserSelection) window.getSelection()?.removeAllRanges();
  emit("selectionChange", null);
}

function pageElementForNode(node: Node | null): HTMLElement | null {
  const element = node instanceof HTMLElement ? node : node?.parentElement;
  return element?.closest<HTMLElement>("[data-page-number]") ?? null;
}

watch(() => [props.sourceUrl, props.fileHash, props.documentId], loadPdf, {
  immediate: true,
});
watch(
  () => props.annotations,
  () => refreshHighlights(props.annotations, mappings, props.fileHash),
);
watch(
  () => props.selectionEpoch,
  () => {
    clearSelection();
    void loadPdf();
  },
);
watch(
  () => props.selectedAnnotationId,
  async (annotationId) => {
    if (!annotationId) return;
    await nextTick();
    const highlight = readerElement.value?.querySelector<HTMLElement>(
      `[data-annotation-id="${annotationId}"]`,
    );
    const annotation = props.annotations.find(
      (item) => item.id === annotationId,
    );
    if (!annotation || annotation.version_status !== "current") return;
    const generation = renderVersion;
    const anchorId =
      annotation.resolved_source_anchor_id ?? annotation.source_anchor_id;
    let targetPage = annotation.page_number;
    if (anchorId) {
      try {
        const anchor = await sourceAnchorsApi.get(anchorId);
        if (
          generation !== renderVersion ||
          props.selectedAnnotationId !== annotationId
        )
          return;
        if (
          anchor.file_hash !== props.fileHash ||
          anchor.resolution_status !== "exact"
        )
          return;
        targetPage = anchor.fragments[0]?.page_number ?? targetPage;
      } catch {
        selectionError.value = "锚点读取失败，请重试定位。";
        return;
      }
    }
    pageInput.value = targetPage;
    await navigatePage();
    await pageScheduler.whenIdle();
    if (
      generation !== renderVersion ||
      props.selectedAnnotationId !== annotationId
    )
      return;
    const target =
      readerElement.value?.querySelector<HTMLElement>(
        `[data-annotation-id="${annotationId}"]`,
      ) ??
      highlight ??
      readerElement.value?.querySelector<HTMLElement>(
        `.pdf-page[data-page-number="${targetPage}"]`,
      );
    target?.scrollIntoView({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
      block: "center",
    });
  },
);

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function cancelPageRenders(): void {
  for (const task of activeRenderTasks.values()) task.cancel();
  activeRenderTasks.clear();
  for (const request of activeMappingRequests.values()) request.abort();
  activeMappingRequests.clear();
}

onBeforeUnmount(() => {
  document.removeEventListener("selectionchange", handleSelectionChange);
  renderVersion += 1;
  pageWindow.disconnect();
  visibleSegments.clear();
  cancelPageRenders();
  pageScheduler.invalidate(renderVersion);
  clearHighlights();
  loadingTask?.destroy();
  documentProxy = null;
});

onMounted(() => {
  document.addEventListener("selectionchange", handleSelectionChange);
});

/** 工作区只调用这些受控入口，避免直接触碰 PDF.js 实例或跨代页面缓存。 */
async function goToPage(page: number): Promise<void> {
  pageInput.value = Math.min(
    Math.max(1, Math.trunc(page)),
    pageNumbers.value.length || 1,
  );
  await navigatePage();
}

async function zoomBy(delta: number): Promise<void> {
  await changeZoom(delta);
}

defineExpose({ locateSourceAnchor, goToPage, zoomBy, currentPage: pageInput });
</script>

<template>
  <section class="pdf-reader" aria-label="PDF 文本批注阅读器">
    <header class="reader-toolbar">
      <div>
        <p class="reader-status" role="status">
          {{
            loading ? "正在渲染 PDF 文本层…" : `缩放 ${Math.round(zoom * 100)}%`
          }}
        </p>
        <p v-if="selectionError" class="selection-error" role="alert">
          {{ selectionError }}
        </p>
        <p v-if="locationStatus" class="reader-status" role="status">
          {{ locationStatus }}
        </p>
        <p
          v-if="visibleSegments.context.value?.primarySegmentId"
          class="reader-status"
          role="status"
        >
          当前段落 #{{ visibleSegments.context.value.primarySegmentId }}
        </p>
        <p
          v-if="visibleSegments.error.value"
          class="selection-error"
          role="alert"
        >
          {{ visibleSegments.error.value }}
        </p>
      </div>
      <div class="zoom-actions" aria-label="PDF 缩放控制">
        <label
          >页码
          <input
            v-model.number="pageInput"
            type="number"
            min="1"
            :max="pageNumbers.length"
            @keydown.enter="navigatePage"
        /></label>
        <button :disabled="loading" @click="navigatePage">跳转</button>
        <button
          :disabled="loading || frozen || zoom <= 0.8"
          aria-label="缩小 PDF"
          @click="changeZoom(-0.15)"
        >
          −
        </button>
        <button
          :disabled="loading || frozen || zoom >= 2"
          aria-label="放大 PDF"
          @click="changeZoom(0.15)"
        >
          ＋
        </button>
      </div>
    </header>
    <p v-if="errorMessage" class="reader-error" role="alert">
      {{ errorMessage }}
    </p>
    <div
      v-else
      ref="readerElement"
      class="pdf-pages"
      @mouseup="captureSelection(true)"
      @scroll.passive="refreshWindow"
      @focusin="refreshWindow"
      @focusout="refreshWindow"
    >
      <PdfPageShell
        v-for="pageNumber in pageNumbers"
        :key="`${sourceUrl}-${renderVersion}-${pageNumber}`"
        :page-number="pageNumber"
        :width="(pageSizes[pageNumber - 1]?.width ?? 0) * zoom"
        :height="(pageSizes[pageNumber - 1]?.height ?? 0) * zoom"
        :error="pageErrors[pageNumber]"
        :annotations="annotationRectsForPage(pageNumber)"
        :selection-rectangles="selectionRectsForPage(pageNumber)"
        :selected-annotation-id="selectedAnnotationId"
        @retry="retryPage"
        @select-annotation="emit('selectAnnotation', $event)"
      />
    </div>
    <nav
      v-if="pageNumbers.length"
      class="thumbnail-strip"
      aria-label="页面缩略图"
    >
      <button
        v-for="pageNumber in thumbnailPages"
        :key="`thumbnail-${pageNumber}`"
        type="button"
        class="thumbnail"
        :class="{ active: pageNumber === pageInput }"
        :data-page-number="pageNumber"
        :aria-label="`转到第 ${pageNumber} 页`"
        :aria-current="pageNumber === pageInput ? 'page' : undefined"
        @click="
          pageInput = pageNumber;
          navigatePage();
        "
      >
        <canvas aria-hidden="true" />
        <b>{{ pageNumber }}</b>
      </button>
    </nav>
    <p
      v-if="!loading && pageNumbers.length > 0 && !hasSelectableText"
      class="selection-hint"
      role="status"
      aria-live="polite"
    >
      此 PDF 未检测到可选择文本，无法创建文字锚点批注。
    </p>
    <p v-else class="selection-hint" role="status" aria-live="polite">
      {{
        selection
          ? "已记录选中文字，可在右侧批注中保存。"
          : "拖选 PDF 正文文字后，可在右侧添加批注。"
      }}
    </p>
  </section>
</template>

<style scoped>
.pdf-reader {
  position: relative;
  display: grid;
  gap: 0.75rem;
}
.reader-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}
.reader-status,
.selection-error,
.selection-hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.82rem;
}
.selection-error,
.reader-error {
  color: var(--color-danger);
}
.zoom-actions {
  display: flex;
  gap: 0.4rem;
}
.zoom-actions input {
  width: 4rem;
  font: inherit;
}
.zoom-actions label {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}
.zoom-actions button,
.add-annotation {
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  padding: 0.4rem 0.65rem;
  background: var(--paper);
  color: var(--text-primary);
  font: inherit;
}
.pdf-pages {
  display: grid;
  justify-content: center;
  gap: 1rem;
  max-height: 74vh;
  overflow: auto;
  padding: 1rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: #dfe6e5;
}
.thumbnail-strip {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  min-height: 82px;
  overflow-x: auto;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: #fff;
}
.thumbnail {
  position: relative;
  display: grid;
  flex: 0 0 64px;
  height: 72px;
  place-items: center;
  overflow: hidden;
  padding: 0;
  border: 1px solid #e1e7f0;
  border-radius: 6px;
  background: #f8fafc;
  color: #172033;
}
.thumbnail.active {
  border: 2px solid #0868f7;
}
.thumbnail canvas {
  max-width: 58px;
  max-height: 62px;
}
.thumbnail b {
  position: absolute;
  bottom: 0;
  min-width: 22px;
  padding: 1px 4px;
  border-radius: 4px 4px 0 0;
  background: #fff;
  font-size: 12px;
}
.thumbnail.active b {
  background: #0868f7;
  color: #fff;
}
@media (prefers-reduced-motion: reduce) {
  .pdf-pages {
    scroll-behavior: auto;
  }
}
</style>
