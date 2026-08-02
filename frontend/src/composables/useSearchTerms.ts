import { computed, shallowRef } from "vue";
import { literatureSearchApi, type BuiltQuery, type ExpandedTerms, type SearchIntentCandidate, type SearchTermGroup } from "../api/literatureSearch";

export function useSearchTerms() {
  const expanded = shallowRef<ExpandedTerms | null>(null);
  const result = shallowRef<BuiltQuery | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const termGroups = computed(() => expanded.value?.term_groups ?? []);

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
  return { expanded, result, termGroups, loading, error, expand, build };
}
