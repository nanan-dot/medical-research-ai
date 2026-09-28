import type { AnalysisStatus, PaperActivity, PaperItem, ReadingStatus, ResearchRole, WorkEntry } from "../../api/paperLibrary";

const READING_LABELS: Readonly<Record<ReadingStatus, string>> = { unread: "未阅读", reading: "阅读中", read: "已阅读" };
const ANALYSIS_LABELS: Readonly<Record<AnalysisStatus, string>> = { not_started: "未分析", pending: "排队中", analyzing: "分析中", completed: "已分析", failed: "分析失败", cancelled: "已取消" };
const ROLE_LABELS: Readonly<Record<ResearchRole, string>> = { core_evidence: "核心证据", background_support: "背景支持", method_reference: "方法参考", supplementary_reading: "补充阅读", to_evaluate: "待评估" };

export function readingLabel(status: ReadingStatus): string { return READING_LABELS[status]; }
export function analysisLabel(status: AnalysisStatus): string { return ANALYSIS_LABELS[status]; }
export function roleLabel(role: ResearchRole | null | undefined): string { return role ? ROLE_LABELS[role] : "待评估"; }

export function entryLabel(kind: "reading" | "analysis", entry: WorkEntry): string {
  const noun = kind === "reading" ? "阅读" : "分析";
  if (entry.action === "continue") return `继续${noun}`;
  if (entry.action === "restart") return `重新${noun}`;
  return `开始${noun}`;
}

export function citationLine(paper: PaperItem): string {
  const leadAuthor = paper.authors?.split(/[;,，]/)[0]?.trim();
  return [leadAuthor ? `${leadAuthor}${paper.authors?.includes(";") ? " et al." : ""}` : null, paper.journal, paper.year].filter(Boolean).join(" · ") || "书目信息待补充";
}

export function activityLabel(activity: PaperActivity): string {
  if (activity.detail) return activity.detail;
  const labels: Readonly<Record<string, string>> = {
    paper_added: "加入论文库", reading_updated: "更新阅读进度", analysis_started: "开始论文分析",
    analysis_updated: "更新论文分析", analysis_completed: "完成论文分析", relation_updated: "更新研究关联",
  };
  return labels[activity.kind] ?? "更新论文工作";
}

export function relativeDate(value: string | null): string {
  if (!value) return "暂无记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const delta = Date.now() - date.getTime();
  const day = 86_400_000;
  if (delta >= 0 && delta < day && date.getDate() === new Date().getDate()) return `今天 ${date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
  if (delta >= 0 && delta < day * 2) return `昨天 ${date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
  return date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}
