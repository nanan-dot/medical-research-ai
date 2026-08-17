import type { SearchResultChange } from "../../api/literatureSearch";

export function isMeaningfulSearchChange(change: SearchResultChange | null | undefined): boolean {
  return change !== null && change !== undefined
    && (change.added_count > 0 || change.removed_count > 0 || change.count_delta !== 0);
}

export function formatSearchChangeNotice(change: SearchResultChange | null | undefined): string | null {
  if (!change || !isMeaningfulSearchChange(change)) return null;
  const meaningfulChange = change;
  const messages: string[] = [];
  if (meaningfulChange.added_count > 0) messages.push(`本次检索发现 ${meaningfulChange.added_count} 篇新增文献`);
  if (meaningfulChange.removed_count > 0) messages.push(`与上次相比，${meaningfulChange.removed_count} 篇文献不再命中当前条件`);
  if (meaningfulChange.added_count === 0 && meaningfulChange.removed_count === 0 && meaningfulChange.count_delta !== 0) {
    messages.push(`结果从 ${meaningfulChange.previous_count} 篇更新为 ${meaningfulChange.current_count} 篇`);
  }
  return messages.join("；");
}
