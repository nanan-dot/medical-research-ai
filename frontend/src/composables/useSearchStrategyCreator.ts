import { computed, onScopeDispose, shallowRef } from "vue";
import { literatureSearchApi, type BuiltQuery, type ExpandedTerms, type ParsedQuery } from "../api/literatureSearch";
import { searchStrategiesApi } from "../api/searchStrategies";
import type { SearchStage } from "../types/searchEntry";
import type { SearchMode } from "../types/searchEntry";

function resolvedIntentMode(mode: SearchMode, candidate: ParsedQuery["candidate"]): string {
  if (mode !== "auto") return mode;
  if (candidate.intervention || candidate.comparison || candidate.outcome) return "pico";
  if (candidate.mechanism || candidate.target) return "mechanism";
  return candidate.disease ? "disease" : "unstructured";
}

/** 入口生成流水线：以序号隔离旧响应，卸载后不再回写界面状态。 */
export function useSearchStrategyCreator() {
  const stage = shallowRef<SearchStage>("idle");
  const error = shallowRef<string | null>(null);
  const isSubmitting = computed(() => !["idle", "failed"].includes(stage.value));
  let requestId = 0;
  let disposed = false;
  onScopeDispose(() => { disposed = true; requestId += 1; });

  async function create(rawTopic: string, mode: SearchMode = "auto"): Promise<{ parsed: ParsedQuery; expanded: ExpandedTerms; built: BuiltQuery; strategyId: number } | null> {
    const currentRequest = ++requestId;
    error.value = null;
    try {
      stage.value = "parse";
      const parsed = await literatureSearchApi.parseQuery(rawTopic);
      if (disposed || currentRequest !== requestId) return null;
      stage.value = "expand";
      const expanded = await literatureSearchApi.expandTerms(parsed.candidate, {});
      if (disposed || currentRequest !== requestId) return null;
      if (expanded.term_groups.length === 0) {
        throw new Error("未能将该问题映射为可执行的 PubMed 英文术语；请补充疾病、干预或英文关键词后重试。");
      }
      stage.value = "build";
      const built = await literatureSearchApi.buildQuery(expanded.term_groups, {});
      if (disposed || currentRequest !== requestId) return null;
      const strategy = await searchStrategiesApi.create({
        research_question: parsed.raw_topic,
        intent_mode: resolvedIntentMode(mode, parsed.candidate),
        intent: parsed.candidate,
        limits: { database: "pubmed" },
        query_text: built.boolean_query,
        terms: expanded.term_groups.flatMap((group) => group.terms.map((term) => ({
          text: term,
          concept_group: group.name,
          source: "smart_expansion" as const,
          field_tag: group.field_tag,
          relation_type: term === group.core_term ? "core" : "synonym",
        }))),
        mesh_terms: [
          ...expanded.mesh_candidates.map((candidate) => ({
          descriptor: candidate.descriptor,
          mesh_id: candidate.mesh_id,
          concept_group: candidate.group_name,
          source: "nlm_mesh" as const,
          verification_status: "verified" as const,
          })),
          // No descriptor is fabricated when NLM is unavailable or returns no
          // exact result. This row preserves the actual checked input and its
          // status so the workspace can offer a truthful retry path.
          ...expanded.term_groups
            .filter((group) => !expanded.mesh_candidates.some((candidate) => candidate.group_name === group.name))
            .flatMap((group) => {
              const status = expanded.mesh_status_by_group?.[group.name];
              return status ? [{
                descriptor: group.core_term,
                mesh_id: null,
                concept_group: group.name,
                source: "nlm_mesh" as const,
                verification_status: status,
              }] : [];
            }),
        ],
      });
      if (disposed || currentRequest !== requestId) return null;
      stage.value = "handoff";
      return { parsed, expanded, built, strategyId: strategy.id };
    } catch (caught) {
      if (!disposed && currentRequest === requestId) {
        stage.value = "failed";
        error.value = caught instanceof Error ? caught.message : "生成检索策略失败，请重试。";
      }
      return null;
    }
  }
  function reset(): void { if (!isSubmitting.value) stage.value = "idle"; }
  return { stage, error, isSubmitting, create, reset };
}
