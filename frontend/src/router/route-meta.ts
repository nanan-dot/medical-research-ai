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
const RESULTS_INDEX_LABEL = "检索结果";
const RESULTS_DISPLAY_LABEL = "结果展示";

// 仅信任 URL 中唯一且合法的来源值，保证刷新、直达和复制链接都有相同的安全降级语义。
function resolveResultBreadcrumb(route: RouteLocationNormalized): string[] {
  if (route.path === "/literature-search/results") {
    return [LITERATURE_SEARCH_LABEL, RESULTS_INDEX_LABEL];
  }

  const origin = route.query.from;
  return origin === ORIGIN_HISTORY
    ? [LITERATURE_SEARCH_LABEL, HISTORY_LABEL, SEARCH_RESULTS_LABEL]
    : [LITERATURE_SEARCH_LABEL, RESULTS_DISPLAY_LABEL];
}

const breadcrumbByPath: Record<string, BreadcrumbDefinition> = {
  "/": ["工作台"],
  "/literature-search": ["文献检索", "检索中心"],
  "/literature-search/workspace": ["文献检索", "检索中心", "检索工作台"],
  "/literature-search/history": ["文献检索", "检索历史"],
  "/literature-search/results": resolveResultBreadcrumb,
  "/recommendations": ["文献检索", "文献推荐"],
  "/sources": ["研究资源", "知识库"],
  "/documents": ["研究资源", "资料库"],
  "/papers": ["研究资源", "论文库"],
  "/paper-research": ["论文研究"],
  "/paper-center": ["论文研究", "论文中心"],
  "/notes": ["研究资源", "笔记库"],
  "/documents/detail": ["研究资源", "资料库", "资料详情"],
};

export const routeMeta = (path: string, breadcrumbPath = path): AppRouteMeta => {
  const feature = featureByPath(path)!;
  return { feature, breadcrumb: breadcrumbByPath[breadcrumbPath] ?? [feature.label] };
};
