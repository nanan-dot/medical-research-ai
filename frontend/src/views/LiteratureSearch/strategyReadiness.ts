import type { SearchStrategyDraft, StrategyValidation } from "../../types/searchStrategy";
import { strategyIntent } from "./strategyIntent";

/** 校验结果只属于它所验证的持久化检索式，编辑或指纹变化后不可复用。 */
export function currentStrategyValidation(strategy: SearchStrategyDraft, query: string, validation: StrategyValidation | null): StrategyValidation | null {
  return query === strategy.query_text && validation?.validated_fingerprint === strategy.fingerprint ? validation : null;
}

/** 后端执行前会再次 validate；未验证不是阻断，字段/语法错误才是。 */
export function strategyReadiness(strategy: SearchStrategyDraft, query: string, validation: StrategyValidation | null) {
  const current = currentStrategyValidation(strategy, query, validation);
  const isSynced = query === strategy.query_text;
  const blocked = !query.trim() || Boolean(current && (!current.is_syntax_valid || !current.are_field_tags_valid || current.blocking_errors.length));
  const queryVerified = isSynced && (current ? !blocked : validation === null && strategy.validation_state === "valid");
  const intent = strategyIntent(strategy);
  const statuses = new Set(strategy.mesh_terms.map((term) => term.verification_status));
  // is_mesh_valid=true 也包含 not_found 和空列表，不能据此声称找到官方主题词。
  const meshVerified = strategy.mesh_terms.length > 0 && statuses.size === 1 && statuses.has("verified");
  const meshLabel = statuses.has("unavailable") ? "MeSH 暂不可用" : statuses.has("stale") ? "MeSH 需刷新" : statuses.has("not_found") ? "MeSH 未找到" : meshVerified ? "MeSH 已验证" : "MeSH 未查询";
  const termWarnings = strategy.terms.filter((term) => term.warning);
  const hasTerms = strategy.terms.length > 0;
  const hasWarnings = !intent.complete || !hasTerms || !meshVerified || termWarnings.length > 0 || Boolean(current?.warnings.length || current?.is_mesh_valid === false);
  const state = blocked ? "blocked" : !queryVerified ? "pending" : hasWarnings ? "warning" : "ready";
  const title = { blocked: "检索策略暂不可执行", pending: "检索式待验证", warning: "可开始检索，请留意提醒", ready: "检索策略已准备就绪" }[state];
  const helper = blocked ? current?.blocking_errors[0]?.message ?? "请补充检索式并修正语法或字段标签。"
    : !isSynced ? "修改尚未保存；保存后再验证或执行。"
      : state === "pending" ? "可先验证；开始检索时后端也会校验当前检索式。"
        : !meshVerified ? "MeSH 状态不影响自由词检索；请确认主题词及研究范围。"
          : state === "warning" ? "请核对研究意图、术语范围和验证提醒，再执行检索。" : "当前检索式已验证，可开始检索。";
  return {
    state, title, helper, canExecute: !blocked && isSynced,
    checks: [
      { label: intent.complete ? (strategy.intent_mode === "pico" ? "PICO 信息完整" : "研究意图已提取") : "研究意图待补充", passed: intent.complete },
      { label: !hasTerms ? "尚无映射术语" : termWarnings.length ? `${termWarnings.length} 个术语有提醒` : `已生成 ${strategy.terms.length} 个术语`, passed: hasTerms && !termWarnings.length },
      { label: meshLabel, passed: meshVerified },
      { label: blocked ? "检索式验证未通过" : queryVerified ? "检索式已验证" : "检索式待验证", passed: queryVerified && !blocked },
    ],
  };
}
