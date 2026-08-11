import type { RouteMeta } from "vue-router";
import { featureByPath } from "../config/features";
import type { FeatureDefinition } from "../types/feature";

export interface AppRouteMeta extends RouteMeta {
  feature: FeatureDefinition;
  breadcrumb: string[];
}

const breadcrumbByPath: Record<string, string[]> = {
  "/": ["工作台"],
  "/literature-search": ["文献检索", "检索工作区"],
  "/literature-search/history": ["文献检索", "检索历史"],
  "/literature-search/results": ["文献检索", "检索结果"],
  "/sources": ["文档与知识", "知识库"],
  "/documents": ["文档与知识", "文档库"],
  "/documents/detail": ["文档与知识", "文档库", "文档详情"],
  "/analysis": ["论文研究", "研究概览"],
  "/chat": ["论文研究", "证据问答"],
};

export const routeMeta = (path: string, breadcrumbPath = path): AppRouteMeta => {
  const feature = featureByPath(path)!;
  return { feature, breadcrumb: breadcrumbByPath[breadcrumbPath] ?? [feature.label] };
};
