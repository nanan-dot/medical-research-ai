import { shallowRef } from "vue";
import { recommendationApi, type RecommendationResponse } from "../api/recommendations";

const STORAGE_KEY = "rag-medicine:recommendations:last-response";

interface StoredRecommendation {
  result: RecommendationResponse;
  savedAt: string;
}

function readStoredRecommendation(): StoredRecommendation | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredRecommendation>;
    if (!parsed.result || typeof parsed.result.query !== "string" || !Array.isArray(parsed.result.items)
      || typeof parsed.savedAt !== "string") return null;
    return parsed as StoredRecommendation;
  } catch {
    return null;
  }
}

export function useRecommendations() {
  const result = shallowRef<RecommendationResponse | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const savedAt = shallowRef<string | null>(null);

  function restore(): RecommendationResponse | null {
    const stored = readStoredRecommendation();
    if (!stored) return null;
    result.value = stored.result;
    savedAt.value = stored.savedAt;
    return stored.result;
  }

  function persist(next: RecommendationResponse): void {
    const nextSavedAt = new Date().toISOString();
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ result: next, savedAt: nextSavedAt }));
      savedAt.value = nextSavedAt;
    } catch {
      savedAt.value = null;
    }
  }

  function clearSaved(): void {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } finally {
      savedAt.value = null;
    }
  }

  async function recommend(query: string, candidateCount: number) {
    loading.value = true;
    error.value = null;
    try {
      const next = await recommendationApi.create(query, candidateCount);
      result.value = next;
      persist(next);
    } catch (requestError) {
      error.value = requestError instanceof Error ? requestError.message : "推荐请求失败";
    } finally {
      loading.value = false;
    }
  }

  return { result, loading, error, savedAt, restore, clearSaved, recommend };
}
