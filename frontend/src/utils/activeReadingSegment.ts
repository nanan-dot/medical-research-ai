export interface SegmentVisibility {
  id: number;
  readingOrder: number;
  visibleRatio: number;
  focusDistance: number;
  isHeading: boolean;
}

/** 滞后阈值是可调交互策略，尚不代表在多设备上冻结的性能参数。 */
export function chooseActiveSegment(candidates: readonly SegmentVisibility[], current: number | null): number | null {
  const score = (item: SegmentVisibility) => item.visibleRatio * .6 + (1 - Math.min(1, item.focusDistance)) * .4 - (item.isHeading ? .15 : 0);
  const sorted = candidates.filter(item => item.visibleRatio > 0)
    .toSorted((left, right) => score(right) - score(left) || left.readingOrder - right.readingOrder);
  const best = sorted[0];
  if (!best) return null;
  const previous = sorted.find(item => item.id === current);
  return previous && score(best) - score(previous) < .12 ? previous.id : best.id;
}
