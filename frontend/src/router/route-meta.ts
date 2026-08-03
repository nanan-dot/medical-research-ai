import type { RouteMeta } from "vue-router";
import { featureByPath } from "../config/features";
import type { FeatureDefinition } from "../types/feature";

export interface AppRouteMeta extends RouteMeta { feature: FeatureDefinition; }
export const routeMeta = (path: string): AppRouteMeta => ({ feature: featureByPath(path)! });
