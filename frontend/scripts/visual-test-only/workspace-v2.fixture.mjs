// visual-test-only: deterministic DTOs for browser screenshots; never import from production source.
export const workspaceStrategyFixture = {
  id: 999,
  research_question: "间质性肺疾病（ILD）患者中，抗纤维化药物的疗效与安全性如何？",
  intent_mode: "pico",
  intent: { disease: "间质性肺疾病 / ILD", intervention: "抗纤维化药物", comparison: "安慰剂 / 标准治疗", outcome: "疗效、安全性、生存率" },
  limits: { date_range: "2010–2026", study_types: ["RCT", "Systematic Review"], language: "中文与英文", full_text: "全文可用优先" },
  query_text: "(\"Interstitial Lung Diseases\"[MeSH] OR ILD[tiab]) AND (nintedanib[tiab] OR pirfenidone[tiab])",
  query_source: "generated", fingerprint: "visual-fixture-fingerprint", revision: 3,
  generation_state: "ready", validation_state: "valid", count_state: "success",
  count: { count: 500, source: "pubmed" }, last_saved_at: "2026-08-23T00:00:00Z",
  // 仅用于视觉验收：复现参考图的 24/10/3 密度，生产代码绝不导入。
  terms: [
    ...["interstitial lung disease", "ILD", "idiopathic pulmonary fibrosis", "pulmonary fibrosis", "diffuse parenchymal lung disease", "interstitial pneumonia"].map((text, index) => ({ id: index + 1, concept_group: "disease", text, source: index ? "smart_expansion" : "research_question", field_tag: "tiab", relation_type: "核心概念", is_locked: index < 2, warning: null })),
    ...["antifibrotic agents", "nintedanib", "pirfenidone", "anti-fibrotic therapy", "tyrosine kinase inhibitor", "TGF-beta inhibitor", "drug treatment"].map((text, index) => ({ id: index + 7, concept_group: "intervention", text, source: index ? "smart_expansion" : "research_question", field_tag: "tiab", relation_type: "药物", is_locked: index === 0, warning: null })),
    ...["treatment outcome", "safety", "survival", "forced vital capacity", "adverse event", "mortality", "quality of life", "disease progression", "hospitalization", "lung function", "clinical response"].map((text, index) => ({ id: index + 14, concept_group: "outcome", text, source: index ? "smart_expansion" : "research_question", field_tag: "tiab", relation_type: "核心结局", is_locked: false, warning: index === 0 ? { code: "TERM_SCOPE_BROAD", message: "术语范围过宽（treatment outcome）", severity: "warning" } : null })),
  ],
  mesh_terms: Array.from({ length: 10 }, (_, index) => ({
    id: index + 1,
    descriptor: ["Interstitial Lung Diseases", "Antifibrotic Agents", "Nintedanib", "Pirfenidone", "Lung Diseases, Interstitial"][index % 5],
    mesh_id: `D00${8410 + index}`,
    concept_group: index < 5 ? "疾病概念" : "干预概念",
    source: "nlm_mesh",
    verification_status: "verified",
    is_locked: index < 3,
    verification_checked_at: "2026-08-23T00:00:00Z",
  })),
  versions: [{ id: 3, strategy_id: 999, version: 3, fingerprint: "visual-fixture-fingerprint", note: null, created_at: "2026-08-23T00:00:00Z" }],
};
