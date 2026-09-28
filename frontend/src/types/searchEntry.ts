export const SEARCH_MODES = ["auto", "pico", "peco", "disease", "mechanism", "custom"] as const;
export type SearchMode = (typeof SEARCH_MODES)[number];
export type SearchStage = "idle" | "parse" | "expand" | "build" | "handoff" | "failed";

export interface SearchTemplate { id: string; title: string; mode: SearchMode; question: string; description: string; }
