import { apiRequest } from "./client";

export type RecommendationStatus = "completed" | "completed_with_warnings" | "unavailable";

export interface RecommendationCitation {
  pmid: string;
  doi: string | null;
  title: string | null;
  authors: string[];
  journal: string | null;
  year: number | null;
  entry_type: string;
  verified: boolean;
  verified_by: string | null;
  verified_on: string | null;
  has_abstract: boolean;
  abstract: string | null;
  publication_types: string[];
  withdrawn: boolean;
}

export interface RecommendationItem {
  citation: RecommendationCitation;
  recommendation_reason: string;
}

export interface RecommendationResponse {
  query: string;
  status: RecommendationStatus;
  items: RecommendationItem[];
  warnings: string[];
}

export const recommendationApi = {
  create: (query: string, candidateCount = 5) =>
    apiRequest<RecommendationResponse>("/recommendations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, candidate_count: candidateCount }),
    }),
};
