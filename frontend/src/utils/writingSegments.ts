import type { ContentSegment } from "../api/writingProjects";

const PARAGRAPH_SEPARATOR = /\n\s*\n/;
const MIN_CHANGED_SEGMENT_SIMILARITY = 0.5;
let fallbackSegmentSequence = 0;

function createSegmentId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `segment-${globalThis.crypto.randomUUID()}`;
  }
  fallbackSegmentSequence += 1;
  return `segment-local-${Date.now()}-${fallbackSegmentSequence}`;
}

function splitParagraphs(draft: string): string[] {
  return draft.split(PARAGRAPH_SEPARATOR).filter((paragraph) => paragraph.trim());
}

function similarity(left: string, right: string): number {
  const leftCharacters = new Set(left.replace(/\s/g, ""));
  const rightCharacters = new Set(right.replace(/\s/g, ""));
  const shared = [...leftCharacters].filter((character) => rightCharacters.has(character)).length;
  return shared / Math.max(leftCharacters.size, rightCharacters.size, 1);
}

/**
 * 先按完全相同的段落匹配，再谨慎匹配小幅改写。这样在段首插入新段落时，
 * 已绑定证据的原段落会保留 ID，而不是因位置变化改指向新文本。
 */
export function reconcileDraftSegments(
  previousSegments: readonly ContentSegment[],
  draft: string,
): ContentSegment[] {
  const paragraphs = splitParagraphs(draft);
  const matchedSegmentIndexes = new Map<number, number>();
  const matchedParagraphIndexes = new Set<number>();

  previousSegments.forEach((segment, segmentIndex) => {
    const paragraphIndex = paragraphs.findIndex(
      (paragraph, index) => !matchedParagraphIndexes.has(index) && paragraph === segment.text,
    );
    if (paragraphIndex >= 0) {
      matchedSegmentIndexes.set(paragraphIndex, segmentIndex);
      matchedParagraphIndexes.add(paragraphIndex);
    }
  });

  const unmatchedSegments = previousSegments.filter(
    (_, index) => ![...matchedSegmentIndexes.values()].includes(index),
  );
  for (const paragraphIndex of paragraphs.keys()) {
    if (matchedSegmentIndexes.has(paragraphIndex)) continue;
    const bestMatch = unmatchedSegments
      .map((segment) => ({ segment, score: similarity(segment.text, paragraphs[paragraphIndex]) }))
      .sort((left, right) => right.score - left.score)[0];
    if (!bestMatch || bestMatch.score < MIN_CHANGED_SEGMENT_SIMILARITY) continue;
    matchedSegmentIndexes.set(paragraphIndex, previousSegments.indexOf(bestMatch.segment));
    unmatchedSegments.splice(unmatchedSegments.indexOf(bestMatch.segment), 1);
  }

  return paragraphs.map((text, paragraphIndex) => {
    const previous = matchedSegmentIndexes.has(paragraphIndex)
      ? previousSegments[matchedSegmentIndexes.get(paragraphIndex)!]
      : undefined;
    return previous ? { ...previous, text } : {
      id: createSegmentId(),
      text,
      origin: "user_provided",
      citation_ids: [],
      pending_item_id: null,
    };
  });
}
