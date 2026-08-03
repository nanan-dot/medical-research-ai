/// <reference types="vite/client" />

import "vue-router";
import type { FeatureDefinition } from "./types/feature";
declare module "vue-router" { interface RouteMeta { feature: FeatureDefinition; } }
