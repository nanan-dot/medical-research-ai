import { computed, reactive, readonly, ref, shallowRef } from "vue";

import {
  DEFAULT_DOCUMENT_FILTERS,
  documentsApi,
  type ContentSearchResult,
  type DocumentFilters,
  type DocumentRecord,
} from "../api/documents";

export const DOCUMENT_PAGE_SIZE = 25;

export function useDocuments() {
  const documents = ref<DocumentRecord[]>([]);
  const contentResults = ref<ContentSearchResult[]>([]);
  const filters = reactive<DocumentFilters>({ ...DEFAULT_DOCUMENT_FILTERS });
  const total = shallowRef(0);
  const offset = shallowRef(0);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let requestSequence = 0;

  const pageNumber = computed(() => Math.floor(offset.value / DOCUMENT_PAGE_SIZE) + 1);
  const hasPrevious = computed(() => offset.value > 0);
  const hasNext = computed(() => offset.value + (filters.mode === "content" ? contentResults.value.length : documents.value.length) < total.value);

  async function run(action: () => Promise<void>): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await action();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "文档请求失败";
    } finally {
      loading.value = false;
    }
  }

  async function load(): Promise<void> {
    const sequence = ++requestSequence;
    await run(async () => {
      const page = filters.mode === "content"
        ? await documentsApi.searchContent(filters, offset.value, DOCUMENT_PAGE_SIZE)
        : await documentsApi.list(filters, offset.value, DOCUMENT_PAGE_SIZE);
      if (sequence !== requestSequence) return;
      total.value = page.total;
      if (filters.mode === "content") {
        contentResults.value = page.items as ContentSearchResult[];
        documents.value = [];
      } else {
        documents.value = page.items as DocumentRecord[];
        contentResults.value = [];
      }
    });
  }

  async function applyFilters(next: DocumentFilters): Promise<void> {
    Object.assign(filters, next);
    offset.value = 0;
    await load();
  }

  async function updateDocument(action: () => Promise<DocumentRecord>): Promise<void> {
    await run(async () => {
      const updated = await action();
      documents.value = documents.value.map((item) => item.id === updated.id ? updated : item);
    });
  }

  const retryParse = (document: DocumentRecord) => updateDocument(() => documentsApi.retryParse(document.id));
  const retryIndex = (document: DocumentRecord) => updateDocument(() => documentsApi.retryIndex(document.id));
  const deleteIndex = (document: DocumentRecord) => updateDocument(() => documentsApi.deleteIndex(document.id));

  async function previousPage(): Promise<void> { offset.value = Math.max(0, offset.value - DOCUMENT_PAGE_SIZE); await load(); }
  async function nextPage(): Promise<void> { offset.value += DOCUMENT_PAGE_SIZE; await load(); }
  async function goToPage(page: number): Promise<void> { offset.value = (Math.max(1, Math.floor(page)) - 1) * DOCUMENT_PAGE_SIZE; await load(); }

  return { documents: readonly(documents), contentResults: readonly(contentResults), filters: readonly(filters), total: readonly(total), loading: readonly(loading), error: readonly(error), pageNumber, hasPrevious, hasNext, load, applyFilters, retryParse, retryIndex, deleteIndex, previousPage, nextPage, goToPage };
}
