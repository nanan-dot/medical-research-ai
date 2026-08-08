import { ref } from "vue";
import { recommendationApi, type RecommendationResponse } from "../api/recommendations";

export function useRecommendations() {
  const result = ref<RecommendationResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function recommend(query: string, candidateCount: number) {
    loading.value = true;
    error.value = null;
    try {
      result.value = await recommendationApi.create(query, candidateCount);
    } catch (requestError) {
      result.value = null;
      error.value = requestError instanceof Error ? requestError.message : "推荐请求失败";
    } finally {
      loading.value = false;
    }
  }

  return { result, loading, error, recommend };
}
