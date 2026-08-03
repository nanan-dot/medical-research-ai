import { apiRequest } from "./client";

export interface HealthStatus { status: string; app: string; version: string; }
export const healthApi = { get: () => apiRequest<HealthStatus>("/health") };
