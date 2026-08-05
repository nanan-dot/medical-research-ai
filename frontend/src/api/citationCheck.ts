import { apiRequest } from "./client";

export type CitationKind = "pmid" | "doi";

export interface CitationAuditItem {
  raw: string;
  kind: CitationKind;
  identifier: string;
  verified: boolean;
  verified_by: string | null;
  verified_on: string | null;
  matched: string | null;
  notes: string[];
}

export interface CitationAuditSummary {
  total: number;
  verified: number;
  unverified: number;
}

export interface CitationCheckResult {
  items: CitationAuditItem[];
  summary: CitationAuditSummary;
}

export const citationCheckApi = {
  check: (text: string) =>
    apiRequest<CitationCheckResult>("/citation-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
};
