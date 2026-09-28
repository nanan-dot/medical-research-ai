import type { ChatCitation } from "../../types/researchChat";
export const sourceLabel = (source: string): string => ({
  user: "你", general: "模型通用回答", paper_grounded: "所选文献证据", mixed: "文献 + 通用解释",
  web_augmented: "外部文献来源", policy: "需要确认", legacy_unknown: "历史回答 · 来源未标注",
}[source] ?? "来源未标注");
export const statusLabel = (status: string | null): string => ({
  answered: "已回答", partial: "部分回答", insufficient_evidence: "证据不足", failed: "未完成",
}[status ?? ""] ?? "");
export const warningLabel = (code: string): string => ({
  insufficient_evidence: "当前范围证据不足", partial_evidence: "部分结论需要核对原文", retrieval_failure: "文献检索失败",
  generation_failure: "模型生成失败，请检查模型设置", web_failure: "外部检索失败", cancelled: "已取消",
  parse_failure: "文档解析失败", index_failure: "文档索引失败", index_not_ready: "文档尚未就绪",
  source_conflict: "来源要求存在冲突", scope_required: "请明确资料范围", web_disabled: "尚未允许外部检索",
  web_query_required: "请填写公开检索词", library_scope_unavailable: "全库检索尚不可用",
  classification_failed: "自动分流未完成，请手动选择模式", classification_unavailable: "请选择回答模式",
  selected_documents_separate_results: "各文献分别检索，结果需交叉核对",
  pubmed_metadata_or_abstract_only: "外部来源限题录或摘要，未读取全文",
}[code] ?? "请结合回答中的限制说明核对结果");
export function citationLink(citation: ChatCitation): string | null {
  if (citation.document_id && Number.isInteger(citation.document_id) && citation.document_id > 0) return "/documents/" + citation.document_id;
  // 只重建允许的来源 URL，拒绝来自模型或外部文本的可执行链接。
  if (citation.pmid && /^\d+$/.test(citation.pmid)) return "https://pubmed.ncbi.nlm.nih.gov/" + citation.pmid + "/";
  return null;
}
