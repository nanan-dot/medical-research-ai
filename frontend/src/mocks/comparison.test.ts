import { describe, expect, it } from "vitest";
import { prototypeCell, prototypeFields, prototypePapers } from "./comparison";

describe("comparison prototype mock adapter", () => {
  it("uses generic demonstration papers and marks unavailable evidence clearly", () => {
    expect(prototypePapers.map((paper) => paper.title)).toEqual(["演示论文 A", "演示论文 B", "演示论文 C"]);
    expect(JSON.stringify(prototypePapers)).not.toMatch(/doi|pmid/i);
    expect(prototypeCell(prototypeFields[0], prototypePapers[0])).toMatchObject({
      value: "研究类型未提供",
      source: "missing",
    });
  });
});
