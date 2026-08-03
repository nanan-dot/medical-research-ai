import { describe, expect, it } from "vitest";
import { directionCandidates, presentationTypes, researchConditions, writingProjects } from "./research-prototype";

describe("FE-06 local prototype adapter", () => {
  it("keeps unknown research conditions explicit", () => {
    expect(researchConditions).toHaveLength(12);
    expect(researchConditions.every((condition) => condition.status === "unknown")).toBe(true);
  });

  it("provides discussion candidates without fabricated publication claims", () => {
    expect(directionCandidates).toHaveLength(3);
    expect(JSON.stringify(directionCandidates)).not.toMatch(/doi|pmid|发表概率|完全没有人做过/i);
  });

  it("offers five local presentation types and clearly local writing drafts", () => {
    expect(presentationTypes).toHaveLength(5);
    expect(writingProjects.every((project) => project.version.startsWith("本地"))).toBe(true);
  });
});
