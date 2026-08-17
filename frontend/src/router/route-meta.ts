import type { RouteLocationNormalized, RouteMeta } from "vue-router";
import { featureByPath } from "../config/features";
import type { FeatureDefinition } from "../types/feature";

export interface AppRouteMeta extends RouteMeta {
  feature: FeatureDefinition;
  breadcrumb: BreadcrumbDefinition;
}

type BreadcrumbDefinition = string[] | ((route: RouteLocationNormalized) => string[]);

const ORIGIN_HISTORY = "history";
const LITERATURE_SEARCH_LABEL = "文献检索";
const HISTORY_LABEL = "历史记录";
const SEARCH_RESULTS_LABEL = "搜索结果";
const RESULTS_DISPLAY_LABEL = "结果展示";

// 仅信任 URL 中唯一且合法的来源值，保证刷新、直达和复制链接都有相同的安全降级语义。
function resolveResultBreadcrumb(route: RouteLocationNormalized): string[] {
  const origin = route.query.from;
  return origin === ORIGIN_HISTORY
    ? [LITERATURE_SEARCH_LABEL, HISTORY_LABEL, SEARCH_RESULTS_LABEL]
    : [LITERATURE_SEARCH_LABEL, RESULTS_DISPLAY_LABEL];
}

const breadcrumbByPath: Record<string, BreadcrumbDefinition> = {
  "/": ["工作台"],
  "/literature-search": ["文献检索", "检索工作区"],
  "/literature-search/history": ["文献检索", "检索历史"],
  "/literature-search/results": resolveResultBreadcrumb,
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
