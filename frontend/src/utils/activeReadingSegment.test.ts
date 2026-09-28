import { expect, it } from "vitest";
import { chooseActiveSegment } from "./activeReadingSegment";

it("keeps a stable paragraph across tiny visibility changes and switches when it leaves", () => {
  const paragraph = { id: 1, readingOrder: 1, visibleRatio: .8, focusDistance: .2, isHeading: false };
  const next = { ...paragraph, id: 2, readingOrder: 2, visibleRatio: .85 };
  expect(chooseActiveSegment([paragraph, next], 1)).toBe(1);
  expect(chooseActiveSegment([next], 1)).toBe(2);
  expect(chooseActiveSegment([], 2)).toBeNull();
});

it("does not let a short heading displace an equally visible paragraph", () => {
  const paragraph = { id: 1, readingOrder: 2, visibleRatio: 1, focusDistance: .2, isHeading: false };
  expect(chooseActiveSegment([paragraph, { ...paragraph, id: 2, readingOrder: 1, isHeading: true }], null)).toBe(1);
});
