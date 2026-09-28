import type { SearchStrategyDraft, StrategyValidation } from "../../types/searchStrategy";

// 仅浏览器/组件验收使用；所有响应在浏览器中拦截，禁止写入真实策略库。
export function searchCenterFixture(): SearchStrategyDraft {
  return {
    id: 999, research_question: "间质性肺疾病（ILD）患者中，抗纤维化药物的疗效与安全性如何？",
    intent_mode: "pico",
    intent: { disease: "间质性肺疾病 / ILD", intervention: "抗纤维化药物", comparison: "安慰剂 / 标准治疗", outcome: "疗效、安全性、生存率" },
    limits: { date_range: "2010–2026", study_types: ["RCT", "Systematic Review"], language: "不限语言", full_text: "全文可用优先" },
    query_text: '("Interstitial Lung Diseases"[MeSH] OR ILD[tiab]) AND nintedanib[tiab]',
    query_source: "generated", fingerprint: "test-fixture-v1", revision: 1,
    generation_state: "ready", validation_state: "valid", count_state: "stale", count: {},
    last_saved_at: "2026-08-31T00:00:00Z",
    terms: [
      ["disease", "interstitial lung disease"], ["disease", "ILD"], ["disease", "idiopathic pulmonary fibrosis"], ["disease", "pulmonary fibrosis"], ["disease", "interstitial pneumonia"],
      ["intervention", "antifibrotic agents"], ["intervention", "nintedanib"], ["intervention", "pirfenidone"],
      ["outcome", "treatment outcome"], ["outcome", "safety"], ["outcome", "survival"],
    ].map(([concept_group, text], index) => ({ id: index + 1, concept_group, text, source: "smart_expansion", field_tag: "tiab", relation_type: "synonym", is_locked: index === 0, warning: null })),
    mesh_terms: [
      ["disease", "Lung Diseases, Interstitial"], ["intervention", "Antifibrotic Agents"], ["outcome", "Treatment Outcome"],
    ].map(([concept_group, descriptor], index) => ({ id: index + 1, concept_group, descriptor, mesh_id: `test-only-${index}`, source: "nlm_mesh", verification_status: "verified", is_locked: false, verification_checked_at: "2026-08-31T00:00:00Z" })),
  };
}

export function searchCenterValidation(strategy: SearchStrategyDraft): StrategyValidation {
  return { is_syntax_valid: true, is_mesh_valid: true, are_field_tags_valid: true, warnings: [], blocking_errors: [], validated_fingerprint: strategy.fingerprint, validated_at: "2026-08-31T00:00:00Z" };
}

export const layoutCases = ["full", "sparse", "unstructured", "unknown", "empty", "not_found", "unavailable"] as const;
export function fixtureForCase(name: (typeof layoutCases)[number]): SearchStrategyDraft {
  const strategy = searchCenterFixture();
  if (name === "full") return strategy;
  if (name === "not_found" || name === "unavailable") {
    strategy.mesh_terms = strategy.mesh_terms.map((term) => ({ ...term, verification_status: name, mesh_id: null }));
    return strategy;
  }
  strategy.terms = strategy.terms.slice(0, 1);
  strategy.mesh_terms = [];
  strategy.limits = {};
  strategy.intent = { disease: "ILD" };
  strategy.validation_state = "stale";
  strategy.query_text = "ILD[tiab]";
  if (name === "unstructured" || name === "unknown") {
    strategy.intent_mode = name === "unknown" ? "future_very_long_intent_mode" : "unstructured";
    strategy.intent = {};
    strategy.terms[0].concept_group = "exposure_future_category";
    strategy.terms[0].text = "interstitial-lung-disease-very-long-original-keyword-without-breaks";
  }
  if (name === "empty") { strategy.terms = []; strategy.query_text = ""; }
  return strategy;
}
