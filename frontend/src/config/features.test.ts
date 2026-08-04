import { expect, it } from "vitest";
import { features, featureByPath } from "./features";

it("keeps future features explicitly labelled and exposes live routes", () => {
  expect(featureByPath("/literature-search")?.status).toBe("LIVE");
  expect(featureByPath("/comparisons")?.status).toBe("MOCK");
  expect(featureByPath("/agent")?.status).toBe("MOCK");
  // 非 LIVE 功能必须：有可路由 path（可访问状态页），且若进导航必须显示三态标识
  expect(features.filter((feature) => feature.status !== "LIVE").every((feature) => feature.path)).toBe(true);
  // 导航项必须带三态状态（不允许无状态裸导航）
  expect(features.filter((feature) => feature.showInNavigation).every((feature) => feature.status !== undefined)).toBe(true);
});
