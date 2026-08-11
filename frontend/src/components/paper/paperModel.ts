import type { AnalysisField, ClaimKind, PaperSource } from "../../api/paperAnalysis";

/**
 * paper 工作区共享展示模型：全部只读派生自 PaperAnalysis 真实字段。
 * 后端不存在的字段一律输出 null，由各组件渲染为"未提供"/"暂无标签"，禁止伪造。
 */

/** 章节导航锚点：由展示层以常量形式提供，不映射到任何后端字段 */
export interface OutlineSection {
  key: string;
  label: string;
}

/** 置信度三态，由 AnalysisField.kind 与来源映射而来 */
export type ConfidenceLevel = "high" | "medium" | "needs-verification";

/** 中央报告区中的一个分析块 */
export interface InsightBlockModel {
  /** structured_result 的键，与后端字段名一一对应 */
  field: string;
  label: string;
  fieldValue: AnalysisField;
  /** 命中该块的证据卡（已按 score 降序） */
  evidenceCards: EvidenceCardModel[];
}

/** 归一化后的来源：local_index 已由 toEvidenceCards 补齐为数组下标 */
export interface ResolvedPaperSource extends PaperSource {
  local_index: number;
}

/** 右侧证据卡：一条已归一化来源的展示视图 */
export interface EvidenceCardModel {
  source: ResolvedPaperSource;
  excerpt: string | null;
  score: number | null;
}

/** 各结构化字段标题。键与后端 17 字段对齐，未列出的键回退到字段名本身 */
export const FIELD_LABELS: Readonly<Record<string, string>> = {
  basic_information: "基本信息",
  one_sentence_conclusion: "一句话结论",
  research_background: "研究背景",
  research_question: "科学问题",
  study_type: "研究设计",
  population: "对象和样本",
  sample_size: "样本量",
  intervention_or_exposure: "干预或暴露",
  comparator: "对照",
  primary_outcome: "主要结局",
  statistical_methods: "统计方法",
  main_results: "主要结果",
  innovations: "创新",
  limitations: "局限",
  next_questions: "下一步阅读",
  original_evidence: "原文证据",
  pending_items: "待确认项",
};

/** 章节导航锚点。仅用于展示层定位，不暗示后端存在阅读状态字段 */
export const OUTLINE_SECTIONS: readonly OutlineSection[] = [
  { key: "abstract", label: "一句话结论" },
  { key: "introduction", label: "研究背景" },
  { key: "methods", label: "研究设计" },
  { key: "results", label: "主要结果" },
  { key: "discussion", label: "讨论与局限" },
  { key: "references", label: "原文证据" },
];

/** kind → 置信度：fact+有来源=High；summary=Medium；inference/not_found=Needs verification */
export function confidenceOf(field: AnalysisField): ConfidenceLevel {
  if (field.kind === "fact" && field.source_indices.length > 0) return "high";
  if (field.kind === "summary") return "medium";
  return "needs-verification";
}

/** 整篇论文的置信度：优先展示 High；无任何 High 时依次取 Medium / Needs verification */
export function overallConfidence(fields: readonly AnalysisField[]): ConfidenceLevel {
  if (fields.some((field) => confidenceOf(field) === "high")) return "high";
  if (fields.some((field) => confidenceOf(field) === "medium")) return "medium";
  return "needs-verification";
}

/** 将后端 sources 包装为展示模型；missing 字段记为 null，来源序号缺失时按数组下标归一化 */
export function toEvidenceCards(sources: readonly PaperSource[]): EvidenceCardModel[] {
  return sources.map((source, index) => {
    const normalized: ResolvedPaperSource = { ...source, local_index: source.local_index ?? index };
    return {
      source: normalized,
      excerpt: source.excerpt ?? null,
      score: source.score ?? null,
    };
  });
}

/**
 * 每张来源卡的证据角色必须由引用它的结构化字段 kind 推导。
 * PaperSource 本身不提供该语义；没有任何字段指向来源时保留为空，交给界面显示“待核对”。
 */
export function toSourceKinds(
  structuredResult: Readonly<Record<string, AnalysisField>> | null,
): ReadonlyMap<number, readonly ClaimKind[]> {
  const sourceKinds = new Map<number, ClaimKind[]>();
  if (!structuredResult) return sourceKinds;

  for (const field of Object.values(structuredResult)) {
    for (const sourceIndex of field.source_indices) {
      const currentKinds = sourceKinds.get(sourceIndex) ?? [];
      if (!currentKinds.includes(field.kind)) currentKinds.push(field.kind);
      sourceKinds.set(sourceIndex, currentKinds);
    }
  }
  return sourceKinds;
}

/** 组装中央报告区块列表：跳过值为空或仅空白的字段 */
export function toInsightBlocks(
  structuredResult: Readonly<Record<string, AnalysisField>>,
  evidenceCards: readonly EvidenceCardModel[],
): InsightBlockModel[] {
  const cards = new Map(evidenceCards.map((card) => [card.source.local_index, card]));
  return Object.entries(structuredResult)
    .map(([field, fieldValue]): InsightBlockModel => {
      const selected = fieldValue.source_indices
        .map((index) => cards.get(index))
        .filter((card): card is EvidenceCardModel => Boolean(card))
        .sort((a, b) => (b.score ?? Number.NEGATIVE_INFINITY) - (a.score ?? Number.NEGATIVE_INFINITY));
      return { field, label: FIELD_LABELS[field] ?? field, fieldValue, evidenceCards: selected };
    })
    .filter((block) => block.fieldValue.value.trim().length > 0);
}
