import { computed, reactive, readonly, ref, shallowRef } from "vue";

import {
  documentsApi,
  type DocumentFilters,
  type DocumentRecord,
} from "../api/documents";

const PAGE_SIZE = 20;

export function useDocuments() {
  const documents = ref<DocumentRecord[]>([]);
  // 文档库默认展示知识源下的全部真实文件；证据问答可用性由用户显式筛选。
  const filters = reactive<DocumentFilters>({ parseStatus: "", indexStatus: "", researchReady: false, knowledgeSourceId: null });
  const total = shallowRef(0);
  const offset = shallowRef(0);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const pageNumber = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1);
  const hasPrevious = computed(() => offset.value > 0);
  const hasNext = computed(() => offset.value + documents.value.length < total.value);

  async function run(action: () => Promise<void>): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await action();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "文档操作失败";
    } finally {
      loading.value = false;
    }
  }

  async function load(): Promise<void> {
    await run(async () => {
      const page = await documentsApi.list(filters, offset.value, PAGE_SIZE);
      documents.value = page.items;
      total.value = page.total;
    });
  }

  async function applyFilters(next: DocumentFilters): Promise<void> {
    filters.parseStatus = next.parseStatus;
    filters.indexStatus = next.indexStatus;
    filters.knowledgeSourceId = next.knowledgeSourceId ?? null;
    filters.query = next.query;
    filters.researchReady = next.researchReady;
    filters.previewableOnly = next.previewableOnly;
    offset.value = 0;
    await load();
  }

  async function updateDocument(action: () => Promise<DocumentRecord>): Promise<void> {
    await run(async () => {
      const updated = await action();
      documents.value = documents.value.map((item) =>
        item.id === updated.id ? updated : item,
      );
    });
  }

  async function retryParse(document: DocumentRecord): Promise<void> {
    if (document.parse_status !== "pending") {
      await updateDocument(() => documentsApi.retryParse(document.id));
      return;
    }
    await run(async () => {
      await documentsApi.parse(document.id);
      await load();
    });
  }
  const retryIndex = (document: DocumentRecord) =>
    updateDocument(() => documentsApi.retryIndex(document.id));
  const deleteIndex = (document: DocumentRecord) =>
    updateDocument(() => documentsApi.deleteIndex(document.id));

  async function previousPage(): Promise<void> {
    offset.value = Math.max(0, offset.value - PAGE_SIZE);
    await load();
  }

  async function nextPage(): Promise<void> {
    offset.value += PAGE_SIZE;
    await load();
  }

  return {
    documents: readonly(documents),
    filters: readonly(filters),
    total: readonly(total),
    loading: readonly(loading),
    error: readonly(error),
    pageNumber,
    hasPrevious,
    hasNext,
    load,
    applyFilters,
    retryParse,
    retryIndex,
    deleteIndex,
    previousPage,
    nextPage,
  };
}
