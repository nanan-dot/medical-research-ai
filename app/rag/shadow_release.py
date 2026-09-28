"""确定性的 Shadow 比较与发布硬门；不执行模型、不改变用户可见答案。"""

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.rag.schemas import RetrievalTrace

StrategyName = Literal[
    "bm25",
    "dense",
    "hybrid_rrf",
    "hybrid_rrf_reranker",
    "grounded",
    "paperqa2",
]
ComparisonStatus = Literal["completed", "unavailable", "failed"]
VISIBLE_MODES = frozenset({"paperqa", "shadow", "grounded"})
REQUIRED_STRATEGIES: tuple[StrategyName, ...] = (
    "bm25",
    "dense",
    "hybrid_rrf",
    "hybrid_rrf_reranker",
    "grounded",
    "paperqa2",
)


class ShadowExecutionError(RuntimeError):
    """可预期的旁路执行失败，不得影响 PaperQA2 主链。"""


class StrategyOutcome(BaseModel):
    """单策略的最小可比较产物；不携带问题、正文或答案文本。"""

    candidate_ids: list[str] = Field(default_factory=list)
    answer_status: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    index_version: str | None = None
    model_version: str | None = None


class StrategyComparison(StrategyOutcome):
    strategy: StrategyName
    status: ComparisonStatus
    reason_code: str | None = None


class ShadowComparison(BaseModel):
    trace_id: str
    comparisons: list[StrategyComparison]

    def by_strategy(self, strategy: StrategyName) -> StrategyComparison:
        return next(item for item in self.comparisons if item.strategy == strategy)


class ShadowStrategy(Protocol):
    def compare(self, trace: RetrievalTrace) -> StrategyOutcome: ...


class ShadowComparisonRunner:
    """将同一 trace 输入各策略；缺失或失败均只记审计状态。"""

    def __init__(self, strategies: dict[str, ShadowStrategy]) -> None:
        self._strategies = strategies

    def compare(self, trace: RetrievalTrace) -> ShadowComparison:
        comparisons: list[StrategyComparison] = []
        for strategy in REQUIRED_STRATEGIES:
            implementation = self._strategies.get(strategy)
            if implementation is None:
                comparisons.append(
                    StrategyComparison(
                        strategy=strategy,
                        status="unavailable",
                        reason_code="strategy_or_model_unavailable",
                    )
                )
                continue
            try:
                outcome = implementation.compare(trace)
                comparisons.append(
                    StrategyComparison(
                        strategy=strategy,
                        status="completed",
                        **outcome.model_dump(),
                    )
                )
            except (ShadowExecutionError, RuntimeError, ValueError):
                comparisons.append(
                    StrategyComparison(
                        strategy=strategy,
                        status="failed",
                        reason_code="strategy_execution_failed",
                    )
                )
        return ShadowComparison(trace_id=trace.trace_id, comparisons=comparisons)


class ReleaseEvidence(BaseModel):
    """冻结报告的硬门事实；缺失必须保持 false，不允许推断为满足。"""

    frozen_report_id: str | None = None
    report_frozen: bool = False
    actual_reranker_available: bool = False
    grounded_generator_available: bool = False
    medical_gold_standard_available: bool = False
    production_latency_budget_frozen: bool = False


class ReleaseDecision(BaseModel):
    release_eligible: bool
    missing_hard_gates: list[str] = Field(default_factory=list)


def evaluate_release_gate(evidence: ReleaseEvidence) -> ReleaseDecision:
    """仅当每项可验证硬门均明确满足时，才允许进入默认发布判定。"""

    checks = {
        "actual_reranker_model": evidence.actual_reranker_available,
        "grounded_generator": evidence.grounded_generator_available,
        "medical_expert_gold_standard": evidence.medical_gold_standard_available,
        "production_latency_budget": evidence.production_latency_budget_frozen,
        "frozen_comparison_report": bool(evidence.frozen_report_id)
        and evidence.report_frozen,
    }
    missing = [name for name, is_satisfied in checks.items() if not is_satisfied]
    return ReleaseDecision(release_eligible=not missing, missing_hard_gates=missing)


def resolve_user_visible_mode(mode: str, *, is_new_chain_enabled: bool) -> str:
    """Feature flag 关闭或 shadow 时始终返回 PaperQA2 的可见链路。"""

    if not is_new_chain_enabled or mode not in VISIBLE_MODES or mode == "shadow":
        return "paperqa"
    return mode


def render_release_report(
    comparison: ShadowComparison, decision: ReleaseDecision
) -> str:
    """生成不含用户问题/文献文本的稳定比较摘要。"""

    lines = [
        f"trace_id: {comparison.trace_id}",
        f"release_eligible: {str(decision.release_eligible).lower()}",
    ]
    lines.extend(f"{item.strategy}: {item.status}" for item in comparison.comparisons)
    if decision.missing_hard_gates:
        lines.append("missing_hard_gates: " + ", ".join(decision.missing_hard_gates))
    return "\n".join(lines)
