import { computed, shallowRef } from "vue";
import { searchStrategiesApi } from "../api/searchStrategies";
import type {
  SearchStrategyDraft,
  SearchStrategyVersion,
  StrategyCount,
  StrategyValidation,
  StrategyVersionComparison,
} from "../types/searchStrategy";

/** Loads backend-authoritative strategy drafts; local state is never treated as saved by itself. */
export function useSearchStrategy() {
  const strategy = shallowRef<SearchStrategyDraft | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const versions = shallowRef<SearchStrategyVersion[]>([]);
  const comparison = shallowRef<StrategyVersionComparison | null>(null);
  const saveState = computed(() => strategy.value === null ? "unsaved" : "saved");

  async function load(strategyId: number): Promise<SearchStrategyDraft | null> {
    loading.value = true;
    error.value = null;
    try {
      strategy.value = await searchStrategiesApi.get(strategyId);
      return strategy.value;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "无法恢复检索策略。";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function refreshMesh(): Promise<void> {
    if (strategy.value === null) return;
    strategy.value = await searchStrategiesApi.refreshMesh(strategy.value.id);
  }

  async function reload(): Promise<SearchStrategyDraft | null> {
    return strategy.value === null ? null : load(strategy.value.id);
  }

  async function addTerm(request: { text: string; concept_group: string }): Promise<void> {
    if (strategy.value === null) return;
    await searchStrategiesApi.addTerm(strategy.value.id, {
      ...request,
      source: "user_added",
    });
    await reload();
  }

  async function patchTerm(termId: number, request: { text?: string; is_locked?: boolean }): Promise<void> {
    if (strategy.value === null) return;
    await searchStrategiesApi.patchTerm(strategy.value.id, termId, request);
    await reload();
  }

  async function deleteTerm(termId: number): Promise<void> {
    if (strategy.value === null) return;
    await searchStrategiesApi.deleteTerm(strategy.value.id, termId);
    await reload();
  }

  async function remapTerms(): Promise<void> {
    if (strategy.value === null) return;
    await searchStrategiesApi.remapTerms(strategy.value.id);
    await reload();
  }

  async function loadVersions(): Promise<void> {
    if (strategy.value === null) return;
    versions.value = await searchStrategiesApi.listVersions(strategy.value.id);
  }

  async function createVersion(): Promise<void> {
    if (strategy.value === null) return;
    await searchStrategiesApi.createVersion(strategy.value.id);
    await loadVersions();
  }

  async function compareVersions(fromVersion: number, toVersion: number): Promise<void> {
    if (strategy.value === null) return;
    comparison.value = await searchStrategiesApi.compareVersions(strategy.value.id, fromVersion, toVersion);
  }

  async function validate(): Promise<StrategyValidation | null> {
    return strategy.value === null ? null : searchStrategiesApi.validate(strategy.value.id);
  }

  async function count(): Promise<StrategyCount | null> {
    if (strategy.value === null) return null;
    return searchStrategiesApi.count(strategy.value.id, strategy.value.fingerprint);
  }

  return {
    strategy,
    loading,
    error,
    saveState,
    versions,
    comparison,
    load,
    reload,
    refreshMesh,
    addTerm,
    patchTerm,
    deleteTerm,
    remapTerms,
    loadVersions,
    createVersion,
    compareVersions,
    validate,
    count,
  };
}
