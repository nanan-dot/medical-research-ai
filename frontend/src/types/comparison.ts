export type ComparisonField =
  | "study_type"
  | "study_population"
  | "sample_size"
  | "intervention"
  | "comparator"
  | "outcome"
  | "methods"
  | "statistics"
  | "results"
  | "novelty"
  | "limitations"
  | "source";

export type ComparisonCellStatus = "generated" | "user_edited" | "missing";

export interface ComparisonSourceRef {
  pmid?: string;
  doi?: string;
  locator: string;
}

export interface ComparisonCell {
  document_id: number;
  field: ComparisonField;
  cell_value: string;
  sources: ComparisonSourceRef[];
  generated_value: string | null;
  user_value: string | null;
  status: ComparisonCellStatus;
}

export interface ComparisonTask {
  id: number;
  selected_document_ids: number[];
  fields: ComparisonField[];
  status: string;
  created_at: string;
  cells: ComparisonCell[];
}
