import { expect, test } from "vitest";
import { fixtureForCase, searchCenterFixture, searchCenterValidation } from "./searchCenter.fixture";
import { strategyReadiness } from "./strategyReadiness";
import { strategyIntent } from "./strategyIntent";

test.each(["not_found", "unavailable", "stale"] as const)("%s MeSH never becomes verified through the validation boolean", (status) => {
  const strategy = searchCenterFixture();
  strategy.mesh_terms[0].verification_status = status;
  const ready = strategyReadiness(strategy, strategy.query_text, searchCenterValidation(strategy));
  expect(ready.state).toBe("warning");
  expect(ready.checks[2].passed).toBe(false);
  expect(ready.canExecute).toBe(true);
});

test.each(["is_syntax_valid", "are_field_tags_valid"] as const)("false %s blocks execution even if error details are absent", (key) => {
  const strategy = searchCenterFixture();
  const validation = searchCenterValidation(strategy);
  validation[key] = false;
  const readiness = strategyReadiness(strategy, strategy.query_text, validation);
  expect(readiness.state).toBe("blocked");
  expect(readiness.canExecute).toBe(false);
});

test("an old fingerprint cannot assert either current success or current errors", () => {
  const strategy = searchCenterFixture();
  const validation = { ...searchCenterValidation(strategy), validated_fingerprint: "old" };
  expect(strategyReadiness(strategy, strategy.query_text, validation).state).toBe("pending");
  validation.blocking_errors = [{ code: "old", message: "old error", severity: "blocking" }];
  expect(strategyReadiness(strategy, strategy.query_text, validation).state).toBe("pending");
});

test("edits immediately invalidate success and prevent execution of the persisted query", () => {
  const strategy = searchCenterFixture();
  const ready = strategyReadiness(strategy, "changed[tiab]", searchCenterValidation(strategy));
  expect(ready.state).toBe("pending");
  expect(ready.canExecute).toBe(false);
});

test("empty query blocks, while a valid free-text query with no mapped terms remains executable with a warning", () => {
  const strategy = fixtureForCase("empty");
  expect(strategyReadiness(strategy, "", null).state).toBe("blocked");
  strategy.query_text = "ILD[tiab]";
  const readiness = strategyReadiness(strategy, strategy.query_text, searchCenterValidation(strategy));
  expect(readiness.state).toBe("warning");
  expect(readiness.canExecute).toBe(true);
});

test("complete validated data is ready, but term and validation warnings are not suppressed", () => {
  const strategy = searchCenterFixture();
  const validation = searchCenterValidation(strategy);
  expect(strategyReadiness(strategy, strategy.query_text, validation).state).toBe("ready");
  validation.warnings = [{ code: "range", message: "检查范围", severity: "warning" }];
  expect(strategyReadiness(strategy, strategy.query_text, validation).state).toBe("warning");
  validation.warnings = [];
  strategy.terms[0].warning = { code: "range", message: "检查范围", severity: "warning" };
  expect(strategyReadiness(strategy, strategy.query_text, validation).state).toBe("warning");
});

test.each(["disease", "mechanism"])("%s intent presents populated concept fields only", (mode) => {
  const strategy = searchCenterFixture();
  strategy.intent_mode = mode;
  strategy.intent = mode === "disease" ? { disease: "ILD" } : { mechanism: "fibrosis", target: "TGF-beta" };
  const intent = strategyIntent(strategy);
  expect(intent.complete).toBe(true);
  expect(intent.fields).toHaveLength(mode === "disease" ? 1 : 2);
  expect(intent.fields.some((field) => field.label.includes("Comparison"))).toBe(false);
});

test("unstructured and unknown modes never imply confirmed intent", () => {
  for (const mode of ["unstructured", "future_intent"]) {
    const strategy = searchCenterFixture();
    strategy.intent_mode = mode;
    strategy.intent = { keywords: ["ILD", "fibrosis"], prompt_version: "must-not-be-a-keyword" };
    const intent = strategyIntent(strategy);
    expect(intent.complete).toBe(false);
    expect(intent.fields).toEqual([{ key: "keywords", label: "当前关键词", value: "ILD、fibrosis" }]);
  }
});
