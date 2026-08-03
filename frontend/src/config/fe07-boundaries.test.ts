import { expect, test } from "vitest";
import { features } from "./features";

test("FE-07 keeps task data live and R4 work explicitly prototyped", () => {
  const byId = (id: string) => features.find((feature) => feature.id === id);
  expect(byId("tasks")?.status).toBe("LIVE");
  expect(byId("agent")?.status).toBe("MOCK");
  expect(byId("evaluation")?.status).toBe("MOCK");
});
