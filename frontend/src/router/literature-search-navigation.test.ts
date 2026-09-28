import { expect, test } from "vitest";

import { router } from "./index";

test("AC-NAV-15 migrates the former history tab URL without a redirect loop", async () => {
  await router.push("/literature-search?tab=history&source=legacy");
  await router.isReady();

  expect(router.currentRoute.value.fullPath).toBe(
    "/literature-search/history?source=legacy",
  );
});

test("AC-NAV-11, AC-NAV-13 and AC-NAV-14 keep the entry and full workspace on their dedicated routes", () => {
  expect(router.resolve("/literature-search").matched[0]?.path).toBe(
    "/literature-search",
  );
  expect(router.resolve("/literature-search/start").matched[0]?.path).toBe(
    "/literature-search/start",
  );
  expect(router.resolve("/literature-search/workspace").matched[0]?.path).toBe(
    "/literature-search/workspace",
  );
  expect(router.resolve("/literature-search/results").matched[0]?.path).toBe(
    "/literature-search/results",
  );
});

test("AC-NAV-07 and AC-NAV-08 preserve result-detail and recommendation deep links", () => {
  expect(
    router.resolve("/literature-search/results/101?task=7").matched[0]?.path,
  ).toBe("/literature-search/results/:id");
  expect(router.resolve("/recommendations").matched[0]?.path).toBe(
    "/recommendations",
  );
});

test("AC-VIS-01 sends an incomplete workspace deep link back to the research-question entry", async () => {
  await router.push("/literature-search/workspace");

  expect(router.currentRoute.value.fullPath).toBe("/literature-search");
});
