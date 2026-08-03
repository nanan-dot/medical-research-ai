import { expect, it } from "vitest";
import { features, featureByPath } from "./features";

it("keeps future features explicitly labelled and exposes live routes", () => {
  expect(featureByPath("/literature-search")?.status).toBe("LIVE");
  expect(featureByPath("/comparisons")?.status).toBe("MOCK");
  expect(featureByPath("/agent")?.status).toBe("MOCK");
  expect(features.filter((feature) => feature.status !== "LIVE").every((feature) => feature.showInNavigation)).toBe(true);
});
