export interface FollowObservation {
  segmentId: number | null;
  now: number;
  hasSelection?: boolean;
  isEditing?: boolean;
  pinnedSegmentId?: number | null;
}

interface FollowPolicyOptions { dwellMs: number }

/** 把滚动噪声收敛为稳定段落；该纯策略不触发网络请求，便于确定性验证。 */
export function createTranslationFollowPolicy(options: FollowPolicyOptions) {
  let generation = "";
  let activeSegmentId: number | null = null;
  let candidateSegmentId: number | null = null;
  let candidateSince = 0;

  function setGeneration(nextGeneration: string): void {
    if (nextGeneration === generation) return;
    generation = nextGeneration;
    activeSegmentId = null;
    candidateSegmentId = null;
    candidateSince = 0;
  }

  function observe(observation: FollowObservation): number | null {
    if (observation.pinnedSegmentId !== undefined && observation.pinnedSegmentId !== null) {
      activeSegmentId = observation.pinnedSegmentId;
      return activeSegmentId;
    }
    if (observation.hasSelection || observation.isEditing) return activeSegmentId;
    if (observation.segmentId === null) {
      candidateSegmentId = null;
      return activeSegmentId;
    }
    if (candidateSegmentId !== observation.segmentId) {
      candidateSegmentId = observation.segmentId;
      candidateSince = observation.now;
      return activeSegmentId;
    }
    if (observation.now - candidateSince < options.dwellMs) return activeSegmentId;
    activeSegmentId = candidateSegmentId;
    return activeSegmentId;
  }

  return { current: () => activeSegmentId, observe, setGeneration };
}
