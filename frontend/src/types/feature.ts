export type FeatureStatus = "LIVE" | "MOCK" | "UNAVAILABLE";
export type FeaturePhase = "FE-01" | "FE-02" | "FE-03" | "FE-04" | "FE-05" | "FE-06" | "FE-07" | "R4-WP05";

export interface FeatureDefinition {
  id: string;
  label: string;
  path: string;
  icon: string;
  group: string;
  phase: FeaturePhase;
  status: FeatureStatus;
  showInNavigation: boolean;
  requiresContextRail: boolean;
  mobileSupport: boolean;
}
