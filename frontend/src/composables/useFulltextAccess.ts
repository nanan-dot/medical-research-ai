import { computed, onUnmounted, shallowRef } from "vue";

import { literatureSearchApi, type CitationItem, type LibraryItem } from "../api/literatureSearch";
import { acquireOfficialPmcFulltext, type OpenFulltextAcquisition } from "../api/openFulltext";

interface UseFulltextAccessOptions {
  resultId: number;
  citation: CitationItem;
  initialItem: LibraryItem | null;
  onUpdated: (item: LibraryItem) => void;
}

export function useFulltextAccess(options: UseFulltextAccessOptions) {
  const item = shallowRef(options.initialItem);
  const acquisition = shallowRef<OpenFulltextAcquisition | null>(null);
  const phase = shallowRef<"idle" | "saving" | "acquiring">("idle");
  const error = shallowRef("");
  let requestVersion = 0;
  let isMounted = true;

  const isBusy = computed(() => phase.value === "saving" || phase.value === "acquiring");
  const hasLocalFulltext = computed(() => item.value?.document_id != null && item.value.fulltext_status === "local_pdf_available");

  async function ensureSaved(): Promise<LibraryItem> {
    if (item.value) return item.value;
    phase.value = "saving";
    const saved = await literatureSearchApi.saveToLibrary(options.resultId, options.citation.pmid);
    item.value = saved;
    if (isMounted) options.onUpdated(saved);
    return saved;
  }

  async function acquirePmc(): Promise<void> {
    if (!options.citation.pmcid || isBusy.value) return;
    const version = ++requestVersion;
    error.value = "";
    try {
      const saved = await ensureSaved();
      phase.value = "acquiring";
      const result = await acquireOfficialPmcFulltext(saved.id, options.citation.pmcid);
      if (!isMounted || version !== requestVersion) return;
      item.value = result.item;
      acquisition.value = result.acquisition;
      options.onUpdated(result.item);
      phase.value = "idle";
    } catch (caught) {
      if (!isMounted || version !== requestVersion) return;
      error.value = caught instanceof Error ? caught.message : "PMC开放全文获取失败";
      phase.value = "idle";
    }
  }

  onUnmounted(() => { isMounted = false; requestVersion += 1; });
  return { item, acquisition, phase, error, isBusy, hasLocalFulltext, acquirePmc };
}
