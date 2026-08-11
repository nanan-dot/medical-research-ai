import { readonly, shallowRef } from "vue";
import { paperResearchApi, type IndexedPaperPage, type PaperResearchOverview } from "../api/paperResearch";

const EMPTY_OVERVIEW: PaperResearchOverview = { recent_analyses: [], pending_confirmations: [], recent_conversations: [] };

export function useResearchOverview() {
  const papers = shallowRef<IndexedPaperPage>({ items: [], total: 0, offset: 0, limit: 10 });
  const overview = shallowRef<PaperResearchOverview>(EMPTY_OVERVIEW);
  const papersLoading = shallowRef(false);
  const overviewLoading = shallowRef(false);
  const papersError = shallowRef<string | null>(null);
  const overviewError = shallowRef<string | null>(null);

  async function loadPapers(query = ""): Promise<void> {
    papersLoading.value = true; papersError.value = null;
    try { papers.value = await paperResearchApi.indexedDocuments(query); }
    catch (cause) { papersError.value = cause instanceof Error ? cause.message : "无法加载已索引论文。"; }
    finally { papersLoading.value = false; }
  }
  async function loadOverview(): Promise<void> {
    overviewLoading.value = true; overviewError.value = null;
    try { overview.value = await paperResearchApi.overview(); }
    catch (cause) { overviewError.value = cause instanceof Error ? cause.message : "无法加载研究概览。"; }
    finally { overviewLoading.value = false; }
  }
  void Promise.all([loadPapers(), loadOverview()]);
  return { papers: readonly(papers), overview: readonly(overview), papersLoading: readonly(papersLoading), overviewLoading: readonly(overviewLoading), papersError: readonly(papersError), overviewError: readonly(overviewError), loadPapers, loadOverview };
}
