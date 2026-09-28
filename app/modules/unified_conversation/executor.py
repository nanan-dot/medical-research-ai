"""路由后的答案编排，只组合来源，不保存伪用户消息。"""

from typing import Protocol

from app.common.exceptions import AppError
from app.integrations.llm.exceptions import LLMClientError
from app.modules.unified_conversation.general_answer_service import (
    GeneralAnswer,
    History,
)
from app.modules.unified_conversation.query_router import RouteDecision
from app.modules.unified_conversation.schema import (
    AnswerContent,
    AnswerMode,
    UnifiedAnswerSection,
    UnifiedMessageCreate,
)


class GeneralProvider(Protocol):
    async def answer(self, question: str, history: History) -> GeneralAnswer: ...


class PaperProvider(Protocol):
    async def answer(self, question: str, document_ids: list[int]) -> AnswerContent: ...


class ExternalProvider(Protocol):
    async def answer(self, query: str) -> AnswerContent: ...


CLARIFICATIONS = {
    "source_conflict": "当前模式与本条问题要求的来源不同。请选择自动模式或调整来源要求。",
    "scope_required": "请明确所指的论文或资料范围，再继续回答。",
    "classification_failed": "暂时无法确定问题所需来源。请明确选择通用模式或仅文献模式。",
    "classification_unavailable": "请明确选择通用模式或仅文献模式。",
    "library_scope_unavailable": "当前支持所选文献范围，请选择具体论文；尚未执行全库检索。",
}


class AnswerExecutor:
    def __init__(
        self, general: GeneralProvider, paper: PaperProvider, external: ExternalProvider
    ) -> None:
        self.general = general
        self.paper = paper
        self.external = external

    async def run(
        self,
        payload: UnifiedMessageCreate,
        route: RouteDecision,
        ids: list[int],
        history: History,
        paper_question: str,
    ) -> tuple[AnswerMode, AnswerContent]:
        if route.requires_scope:
            return route.answer_mode, AnswerContent(
                status="partial",
                warnings=[route.reason_code],
                actions=["select_mode", "select_documents"],
                sections=[
                    UnifiedAnswerSection(
                        source_type="policy",
                        answer_status="partial",
                        content=CLARIFICATIONS.get(
                            route.reason_code, CLARIFICATIONS["scope_required"]
                        ),
                    )
                ],
            )
        if route.answer_mode == AnswerMode.GENERAL:
            return AnswerMode.GENERAL, await self.general_answer(
                payload.message, history
            )
        if route.answer_mode == AnswerMode.WEB_AUGMENTED:
            if (
                not payload.allow_web_search
                or not payload.web_query
                or not payload.web_query.strip()
            ):
                code = (
                    "web_disabled"
                    if not payload.allow_web_search
                    else "web_query_required"
                )
                return AnswerMode.WEB_AUGMENTED, AnswerContent(
                    status="partial",
                    warnings=[code],
                    actions=["enable_web", "edit_web_query"],
                    sections=[
                        UnifiedAnswerSection(
                            source_type="policy",
                            answer_status="partial",
                            content="如需外部来源，请开启联网并填写要发送给 PubMed 的公开检索词。",
                        )
                    ],
                )
            return AnswerMode.WEB_AUGMENTED, await self.external.answer(
                payload.web_query.strip()
            )
        paper = await self.paper.answer(paper_question, ids)
        failures = {
            "retrieval_failure",
            "index_not_ready",
            "index_failure",
            "parse_failure",
            "generation_failure",
        }
        supplement = (
            not route.strict
            and not failures.intersection(paper.warnings)
            and (
                route.answer_mode == AnswerMode.MIXED
                or (
                    payload.allow_general_supplement
                    and paper.status in {"partial", "insufficient_evidence"}
                )
            )
        )
        if not supplement:
            return AnswerMode.PAPER_GROUNDED, paper
        explanation = await self.general_answer(
            "以下问题的论文事实仅由独立文献段回答。你只解释涉及的通用术语、方法或如何核查；"
            "不能给出该论文的样本量、结果、终点等事实或推测。问题：" + payload.message,
            [],
        )
        paper.sections.extend(explanation.sections)
        paper.warnings.extend(explanation.warnings)
        paper.actions.extend(explanation.actions)
        if explanation.status == "failed":
            paper.status = (
                "partial" if paper.status in {"answered", "partial"} else "failed"
            )
        elif paper.status != "answered":
            paper.status = "partial"
        return AnswerMode.MIXED, paper

    async def general_answer(self, question: str, history: History) -> AnswerContent:
        try:
            result = await self.general.answer(question, history)
            return AnswerContent(
                sections=[
                    UnifiedAnswerSection(source_type="general", content=result.content)
                ],
                model_version=result.model_version,
            )
        except (LLMClientError, AppError, TimeoutError):
            return AnswerContent(
                status="failed",
                warnings=["generation_failure"],
                actions=["retry", "configure_model"],
                sections=[
                    UnifiedAnswerSection(
                        source_type="general",
                        answer_status="failed",
                        content="通用回答服务暂时不可用，请检查模型设置后重试。",
                    )
                ],
            )
