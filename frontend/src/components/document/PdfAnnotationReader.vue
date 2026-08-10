<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, shallowRef, useTemplateRef, watch } from "vue";
import {
  getDocument,
  GlobalWorkerOptions,
  TextLayer,
  type PDFDocumentLoadingTask,
  type PDFDocumentProxy,
} from "pdfjs-dist/legacy/build/pdf.mjs";
import workerSource from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?url";

import type { AnnotationRect, DocumentAnnotation } from "../../api/documentAnnotations";
import type { PdfTextSelection } from "../../types/documentAnnotations";

GlobalWorkerOptions.workerSrc = workerSource;

const props = defineProps<{
  sourceUrl: string;
  annotations: readonly DocumentAnnotation[];
  selectedAnnotationId: number | null;
}>();

const emit = defineEmits<{
  selectionChange: [selection: PdfTextSelection | null];
  requestAnnotation: [];
  selectAnnotation: [annotationId: number];
}>();

const readerElement = useTemplateRef<HTMLElement>("readerElement");
const pageNumbers = shallowRef<number[]>([]);
const loading = shallowRef(false);
const errorMessage = shallowRef<string | null>(null);
const selectionError = shallowRef<string | null>(null);
const selection = shallowRef<PdfTextSelection | null>(null);
const zoom = shallowRef(1.25);
let documentProxy: PDFDocumentProxy | null = null;
let loadingTask: PDFDocumentLoadingTask | null = null;
let renderVersion = 0;

const annotationRects = computed(() => {
  const byPage = new Map<number, Array<{ annotation: DocumentAnnotation; rect: AnnotationRect }>>();
  for (const annotation of props.annotations) {
    if (annotation.version_status !== "current") continue;
    const pageRects = byPage.get(annotation.page_number) ?? [];
    for (const rect of annotation.rectangles) pageRects.push({ annotation, rect });
    byPage.set(annotation.page_number, pageRects);
  }
  return byPage;
});

function annotationRectsForPage(pageNumber: number) {
  return annotationRects.value.get(pageNumber) ?? [];
}

function annotationStyle(rect: AnnotationRect, color: DocumentAnnotation["color"]) {
  return {
    left: `${rect.left * 100}%`,
    top: `${rect.top * 100}%`,
    width: `${rect.width * 100}%`,
    height: `${rect.height * 100}%`,
    backgroundColor: annotationColor(color),
  };
}

function annotationColor(color: DocumentAnnotation["color"]): string {
  return {
    yellow: "rgba(246, 203, 73, .42)",
    green: "rgba(106, 190, 128, .38)",
    blue: "rgba(102, 164, 223, .38)",
    pink: "rgba(219, 123, 163, .38)",
  }[color];
}

async function loadPdf(): Promise<void> {
  const currentRenderVersion = ++renderVersion;
  loadingTask?.destroy();
  documentProxy = null;
  pageNumbers.value = [];
  clearSelection();
  loading.value = true;
  errorMessage.value = null;
  try {
    loadingTask = getDocument({ url: props.sourceUrl });
    documentProxy = await loadingTask.promise;
    if (currentRenderVersion !== renderVersion) return;
    pageNumbers.value = Array.from({ length: documentProxy.numPages }, (_, index) => index + 1);
    await nextTick();
    await renderPages(documentProxy, currentRenderVersion);
  } catch (cause) {
    if (currentRenderVersion !== renderVersion) return;
    errorMessage.value = cause instanceof Error ? cause.message : "无法加载 PDF 原文";
  } finally {
    if (currentRenderVersion === renderVersion) loading.value = false;
  }
}

async function renderPages(pdf: PDFDocumentProxy, currentRenderVersion: number): Promise<void> {
  for (const pageNumber of pageNumbers.value) {
    if (currentRenderVersion !== renderVersion) return;
    await renderPage(pdf, pageNumber);
  }
}

async function renderPage(pdf: PDFDocumentProxy, pageNumber: number): Promise<void> {
  const page = await pdf.getPage(pageNumber);
  const viewport = page.getViewport({ scale: zoom.value });
  const pageElement = readerElement.value?.querySelector<HTMLElement>(`[data-page-number="${pageNumber}"]`);
  const canvas = pageElement?.querySelector<HTMLCanvasElement>("canvas");
  const textLayerElement = pageElement?.querySelector<HTMLElement>(".text-layer");
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
  await page.render({
    canvas,
    canvasContext: context,
    viewport,
    transform: [pixelRatio, 0, 0, pixelRatio, 0, 0],
  }).promise;

  textLayerElement.replaceChildren();
  textLayerElement.style.setProperty("--scale-factor", String(viewport.scale));
  const textLayer = new TextLayer({
    textContentSource: await page.getTextContent(),
    container: textLayerElement,
    viewport,
  });
  await textLayer.render();
}

async function changeZoom(delta: number): Promise<void> {
  const nextZoom = Math.min(2, Math.max(.8, zoom.value + delta));
  if (nextZoom === zoom.value || !documentProxy) return;
  zoom.value = nextZoom;
  await nextTick();
  await renderPages(documentProxy, renderVersion);
}

function captureSelection(): void {
  const browserSelection = window.getSelection();
  if (!browserSelection || browserSelection.rangeCount === 0) return clearSelection();
  const selectedText = browserSelection.toString().split(/\s+/).filter(Boolean).join(" ");
  if (!selectedText) return clearSelection();
  const startPage = pageElementForNode(browserSelection.anchorNode);
  const endPage = pageElementForNode(browserSelection.focusNode);
  if (!startPage || startPage !== endPage) {
    selectionError.value = "批注选区必须位于同一页 PDF。";
    return clearSelection(false);
  }
  const pageBounds = startPage.getBoundingClientRect();
  const rectangles = Array.from(browserSelection.getRangeAt(0).getClientRects())
    .filter((rect) => rect.width > 0 && rect.height > 0)
    .map((rect) => selectionRect(rect, pageBounds));
  if (rectangles.length === 0) return clearSelection();
  const nextSelection = {
    pageNumber: Number(startPage.dataset.pageNumber),
    rectangles,
    selectedText,
  };
  selectionError.value = null;
  selection.value = nextSelection;
  emit("selectionChange", nextSelection);
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

function clamp(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function selectionRect(rect: DOMRect, pageBounds: DOMRect): AnnotationRect {
  const left = clamp((rect.left - pageBounds.left) / pageBounds.width);
  const top = clamp((rect.top - pageBounds.top) / pageBounds.height);
  return {
    left,
    top,
    width: Math.min(1 - left, clamp(rect.width / pageBounds.width)),
    height: Math.min(1 - top, clamp(rect.height / pageBounds.height)),
  };
}

watch(() => props.sourceUrl, loadPdf, { immediate: true });
watch(() => props.selectedAnnotationId, async (annotationId) => {
  if (!annotationId) return;
  await nextTick();
  readerElement.value
    ?.querySelector<HTMLElement>(`[data-annotation-id="${annotationId}"]`)
    ?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "center" });
});

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

onBeforeUnmount(() => {
  renderVersion += 1;
  loadingTask?.destroy();
  documentProxy = null;
});
</script>

<template>
  <section class="pdf-reader" aria-label="PDF 文本批注阅读器">
    <header class="reader-toolbar">
      <div>
        <p class="reader-status" role="status">{{ loading ? "正在渲染 PDF 文本层…" : `缩放 ${Math.round(zoom * 100)}%` }}</p>
        <p v-if="selectionError" class="selection-error" role="alert">{{ selectionError }}</p>
      </div>
      <div class="zoom-actions" aria-label="PDF 缩放控制">
        <button :disabled="loading || zoom <= .8" aria-label="缩小 PDF" @click="changeZoom(-.15)">−</button>
        <button :disabled="loading || zoom >= 2" aria-label="放大 PDF" @click="changeZoom(.15)">＋</button>
      </div>
    </header>
    <p v-if="errorMessage" class="reader-error" role="alert">{{ errorMessage }}</p>
    <div v-else ref="readerElement" class="pdf-pages" @mouseup="captureSelection">
      <div v-for="pageNumber in pageNumbers" :key="pageNumber" class="pdf-page" :data-page-number="pageNumber">
        <canvas class="pdf-canvas" />
        <div class="text-layer" aria-label="可选择的 PDF 文本" />
        <div class="annotation-layer">
          <button
            v-for="item in annotationRectsForPage(pageNumber)"
            :key="`${item.annotation.id}-${item.rect.left}-${item.rect.top}`"
            class="annotation-highlight"
            :class="{ 'annotation-highlight-selected': item.annotation.id === props.selectedAnnotationId }"
            :data-annotation-id="item.annotation.id"
            :style="annotationStyle(item.rect, item.annotation.color)"
            :aria-label="`定位批注 ${item.annotation.id}`"
            @click.stop="emit('selectAnnotation', item.annotation.id)"
          />
        </div>
      </div>
    </div>
    <button v-if="selection" class="add-annotation" @click="emit('requestAnnotation')">添加批注</button>
  </section>
</template>

<style scoped>
.pdf-reader { position: relative; display: grid; gap: .75rem; }
.reader-toolbar { display: flex; justify-content: space-between; align-items: center; gap: .75rem; }
.reader-status, .selection-error { margin: 0; color: var(--text-muted); font-size: .82rem; }
.selection-error, .reader-error { color: var(--color-danger); }
.zoom-actions { display: flex; gap: .4rem; }
.zoom-actions button, .add-annotation { border: 1px solid var(--border-strong); border-radius: 7px; padding: .4rem .65rem; background: var(--paper); color: var(--text-primary); font: inherit; }
.pdf-pages { display: grid; justify-content: center; gap: 1rem; max-height: 74vh; overflow: auto; padding: 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: #dfe6e5; }
.pdf-page { position: relative; max-width: 100%; box-shadow: var(--shadow-card); background: white; }
.pdf-canvas { display: block; }
.text-layer { position: absolute; inset: 0; overflow: hidden; line-height: 1; text-size-adjust: none; transform-origin: 0 0; }
.text-layer :deep(span), .text-layer :deep(br) { position: absolute; color: transparent; cursor: text; transform-origin: 0 0; }
.text-layer :deep(::selection) { background: rgba(57, 131, 212, .35); }
.annotation-layer { position: absolute; inset: 0; pointer-events: none; }
.annotation-highlight { position: absolute; border: 0; border-radius: 2px; pointer-events: auto; cursor: pointer; }
.annotation-highlight-selected { outline: 2px solid var(--color-primary); outline-offset: 1px; }
.add-annotation { justify-self: end; border-color: var(--color-primary); background: var(--color-primary); color: #fff; font-weight: 750; }
@media (prefers-reduced-motion: reduce) { .pdf-pages { scroll-behavior: auto; } }
</style>
