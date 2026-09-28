export type TranslationRequestPriority = "active" | "adjacent" | "prefetch";

export interface TranslationPrefetchCandidate {
  segmentId: number;
  priority: TranslationRequestPriority;
  distance: number;
}

export interface TranslationPrefetchEnvironment {
  followEnabled: boolean;
  isBackground: boolean;
  saveData: boolean;
  effectiveType: string | null;
}

const PRIORITY_WEIGHT: Record<TranslationRequestPriority, number> = { active: 3, adjacent: 2, prefetch: 1 };

export function shouldPrefetch(environment: TranslationPrefetchEnvironment): boolean {
  return environment.followEnabled && !environment.isBackground && !environment.saveData &&
    environment.effectiveType !== "slow-2g" && environment.effectiveType !== "2g";
}

/** 返回有界且稳定的队列；同段只保留最高优先级，避免滚动时形成请求风暴。 */
export function rankTranslationCandidates(
  candidates: readonly TranslationPrefetchCandidate[],
  limit: number,
): TranslationPrefetchCandidate[] {
  const unique = new Map<number, TranslationPrefetchCandidate>();
  for (const candidate of candidates) {
    const previous = unique.get(candidate.segmentId);
    if (!previous || PRIORITY_WEIGHT[candidate.priority] > PRIORITY_WEIGHT[previous.priority] ||
      (candidate.priority === previous.priority && candidate.distance < previous.distance)) unique.set(candidate.segmentId, candidate);
  }
  return [...unique.values()].toSorted((left, right) =>
    PRIORITY_WEIGHT[right.priority] - PRIORITY_WEIGHT[left.priority] || left.distance - right.distance || left.segmentId - right.segmentId,
  ).slice(0, Math.max(0, limit));
}
