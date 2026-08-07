import { computed, shallowRef } from "vue";
import { literatureSearchApi, type BuiltQuery, type ExpandedTerms, type LiteratureSearchTask, type SearchIntentCandidate, type SearchTermGroup } from "../api/literatureSearch";

export function useSearchTerms() {
  const expanded = shallowRef<ExpandedTerms | null>(null);
  const result = shallowRef<BuiltQuery | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const termGroups = computed(() => expanded.value?.term_groups ?? []);

  // 执行检索任务（R2-WP04）：把 build-query 输出的检索式提交为任务并立即
  // 执行；创建成功后跳转由调用方处理。空检索式视为无效，不发起请求。
  const taskLoading = shallowRef(false);
  const taskError = shallowRef<string | null>(null);

  async function expand(candidate: SearchIntentCandidate) {
    loading.value = true; error.value = null; result.value = null;
    try { expanded.value = await literatureSearchApi.expandTerms(candidate, {}); }
    catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to expand terms"; }
    finally { loading.value = false; }
  }
  async function build(groups: SearchTermGroup[]) {
    loading.value = true; error.value = null;
    try { result.value = await literatureSearchApi.buildQuery(groups, {}); }
    catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to build query"; }
    finally { loading.value = false; }
  }
  async function createTask(input: {
    original_query: string;
    structured_query: string;
    search_string: string;
    filters: string;
    model_version: string;
    user_edits: string;
    retmax: number;
  }): Promise<LiteratureSearchTask | null> {
    taskLoading.value = true; taskError.value = null;
    try {
      const task = await literatureSearchApi.createTask({
        database: "pubmed",
        ...input,
      });
      return task;
    } catch (caught) {
      taskError.value = caught instanceof Error ? caught.message : "无法创建检索任务";
      return null;
    } finally {
      taskLoading.value = false;
    }
  }
  return { expanded, result, termGroups, loading, error, taskLoading, taskError, expand, build, createTask };
}
