export type OriginKind = "用户" | "论文证据" | "模型总结" | "模型推断" | "待确认";

export interface ResearchCondition {
  id: string;
  label: string;
  value: string;
  status: "known" | "unknown";
}

export interface DirectionCandidate {
  id: string;
  title: string;
  question: string;
  evidence: string;
  controversy: string;
  feasibility: string;
  risk: string;
  searchNext: string;
  advisorCheck: string;
}

export interface PresentationDraft {
  id: string;
  title: string;
  type: string;
  progress: string;
  evidenceStatus: string;
  pending: string;
  updatedAt: string;
}

export interface WritingProject {
  id: string;
  title: string;
  type: string;
  version: string;
  updatedAt: string;
  origin: OriginKind;
}
