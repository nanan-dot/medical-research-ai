"""保守的 Agent 任务分类器：固定任务优先，复杂任务才进入 Agent。"""

from collections.abc import Callable
from dataclasses import dataclass

from app.agents.schemas import AgentTaskType, TaskDecision

ComplexTaskClassifier = Callable[[str], TaskDecision | None]


@dataclass(frozen=True)
class RoutePolicy:
    """一个任务类型的关键词、固定工具和固定工作流策略。"""

    task_type: AgentTaskType
    keywords: tuple[str, ...]
    required_tools: tuple[str, ...]


ROUTE_POLICIES: tuple[RoutePolicy, ...] = (
    RoutePolicy(AgentTaskType.SINGLE_PAPER_QA, ("单篇", "这篇", "pdf"), ("paper_qa",)),
    RoutePolicy(AgentTaskType.NOTE_QA, ("笔记", "我的笔记", "note"), ("local_note_search",)),
    RoutePolicy(AgentTaskType.EXTERNAL_SEARCH, ("外部文献", "pubmed", "最新文献", "检索"), ("pubmed_search",)),
    RoutePolicy(AgentTaskType.MULTI_PAPER_COMPARISON, ("多篇", "比较", "对比", "几篇"), ("comparison_service",)),
    RoutePolicy(AgentTaskType.CANDIDATE_DIRECTION, ("候选方向", "研究方向", "创新方向"), ("research_direction_service",)),
    RoutePolicy(AgentTaskType.WRITING_OUTLINE, ("写作提纲", "提纲", "大纲", "outline"), ("outline_service",)),
)

COMPLEX_CONFIDENCE = 0.92
SIMPLE_CONFIDENCE = 0.98
CLARIFICATION_CONFIDENCE = 0.3


class AgentTaskClassifier:
    """对任务进行白名单工具路由，默认不把模糊请求升级为 Agent。"""

    def __init__(self, complex_classifier: ComplexTaskClassifier | None = None) -> None:
        self._complex_classifier = complex_classifier

    def classify(self, query: str) -> TaskDecision:
        """返回分类决定，不执行路由后的服务或工具。"""

        normalized_query = query.casefold().strip()
        matching_policies = self._find_matching_policies(normalized_query)
        if len(matching_policies) >= 2:
            return self._build_complex_decision(matching_policies)
        if len(matching_policies) == 1:
            return self._build_simple_decision(matching_policies[0])
        return self._classify_unmatched_query(query)

    @staticmethod
    def _find_matching_policies(normalized_query: str) -> list[RoutePolicy]:
        return [
            policy
            for policy in ROUTE_POLICIES
            if any(keyword in normalized_query for keyword in policy.keywords)
        ]

    @staticmethod
    def _build_simple_decision(policy: RoutePolicy) -> TaskDecision:
        return TaskDecision(
            task_type=policy.task_type,
            required_tools=list(policy.required_tools),
            use_agent=False,
            clarification_needed=False,
            reason="任务命中单一固定工作流，未启用 Agent。",
            confidence=SIMPLE_CONFIDENCE,
        )

    @staticmethod
    def _build_complex_decision(matching_policies: list[RoutePolicy]) -> TaskDecision:
        return TaskDecision(
            task_type=AgentTaskType.COMPLEX_RESEARCH,
            required_tools=AgentTaskClassifier._combine_tools(matching_policies),
            use_agent=True,
            clarification_needed=False,
            reason="任务同时命中多个受控工作流，需要 Agent 编排已授权工具。",
            confidence=COMPLEX_CONFIDENCE,
        )

    def _classify_unmatched_query(self, query: str) -> TaskDecision:
        if self._complex_classifier is not None:
            candidate = self._complex_classifier(query)
            if candidate is not None and self._is_safe_model_decision(candidate):
                return candidate
        return TaskDecision(
            task_type=AgentTaskType.CLARIFICATION,
            required_tools=[],
            use_agent=False,
            clarification_needed=True,
            reason="无法从显式规则确定任务类型，请用户补充目标、资料范围或期望输出。",
            confidence=CLARIFICATION_CONFIDENCE,
        )

    @staticmethod
    def _combine_tools(matching_policies: list[RoutePolicy]) -> list[str]:
        tools: list[str] = []
        for policy in matching_policies:
            for tool in policy.required_tools:
                if tool not in tools:
                    tools.append(tool)
        if "citation_check" not in tools:
            tools.append("citation_check")
        return tools

    @staticmethod
    def _is_safe_model_decision(candidate: TaskDecision) -> bool:
        """仅接纳高置信复杂任务建议，工具仍由后续受控注册表校验。"""

        return (
            candidate.task_type is AgentTaskType.COMPLEX_RESEARCH
            and candidate.use_agent
            and not candidate.clarification_needed
            and candidate.confidence >= COMPLEX_CONFIDENCE
        )
