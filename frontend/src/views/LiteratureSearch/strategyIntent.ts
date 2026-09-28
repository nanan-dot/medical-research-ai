import type { SearchStrategyDraft } from "../../types/searchStrategy";

export interface StrategyIntentField { key: string; label: string; value: string }
const fieldLabels: Record<string, string> = { disease: "疾病 / 人群", intervention: "干预", comparison: "对照", outcome: "结局", target: "靶点", mechanism: "机制" };
function textValue(value: unknown): string { return typeof value === "string" ? value.trim() : ""; }

/** 展示后端已提供的研究意图，不由空字段推断医学概念。 */
export function strategyIntent(strategy: SearchStrategyDraft) {
  const value = (key: string) => textValue(strategy.intent[key]);
  const disease = value("disease") || value("population");
  if (strategy.intent_mode === "pico") {
    const fields: StrategyIntentField[] = [
      { key: "P", label: "人群（Population）", value: disease },
      { key: "I", label: "干预（Intervention）", value: value("intervention") },
      { key: "C", label: "对照（Comparison）", value: value("comparison") },
      { key: "O", label: "结局（Outcome）", value: value("outcome") },
    ];
    return { label: "PICO", fields, isStructured: true, complete: fields.every((field) => field.value.length > 0) };
  }
  const labels: Record<string, string> = { disease: "疾病检索", mechanism: "机制检索", unstructured: "自由关键词检索" };
  const isStructured = ["disease", "mechanism"].includes(strategy.intent_mode);
  const fields = isStructured ? Object.entries(fieldLabels).flatMap(([key, label]) => {
    const text = key === "disease" ? disease : value(key);
    return text ? [{ key, label, value: text }] : [];
  }) : [];
  if (!fields.length) {
    const keywords = Array.isArray(strategy.intent.keywords) ? strategy.intent.keywords.map(textValue).filter(Boolean).join("、") : value("keywords");
    fields.push({ key: "keywords", label: "当前关键词", value: keywords || value("topic") || strategy.research_question });
  }
  const complete = strategy.intent_mode === "disease" ? Boolean(disease) : strategy.intent_mode === "mechanism" && Boolean(value("mechanism") || value("target"));
  return { label: labels[strategy.intent_mode] ?? "研究意图待确认", fields, isStructured, complete };
}
