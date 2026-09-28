"""Constrained optional LLM wording over deterministic recommendation evidence."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.integrations.llm.schemas import ChatMessage, LLMResponse
from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.reason_pipeline import (
    PolishedReasonOutput,
    RecommendationReasonFactPacket,
    narration_prompt,
    validate_polished_reason,
)

logger = logging.getLogger(__name__)
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
UNSUPPORTED_CERTAINTY_PATTERN = re.compile(
    r"证明|证实|显著改善|显著降低|应当采用|必然|因果"
)


class NarrationValidationError(ValueError):
    """The model response could not safely replace deterministic evidence text."""


class NarrationLLM(Protocol):
    async def chat(self, messages: list[ChatMessage]) -> LLMResponse: ...

    async def aclose(self) -> None: ...


class NarrationOutput(BaseModel):
    headline: str = Field(min_length=1, max_length=80)
    narrative: str = Field(min_length=40, max_length=220)


@dataclass(frozen=True)
class NarrativeResult:
    headline: str
    narrative: str
    limitation: str | None


@dataclass(frozen=True)
class PacketNarrativeResult:
    output: PolishedReasonOutput | None
    error_code: str | None
    model: str | None


class RecommendationNarrator:
    """LLM may compress wording but cannot change identity or computed facts."""

    def __init__(self, llm: NarrationLLM | None = None) -> None:
        self._llm = llm

    async def render_packet(
        self, packet: RecommendationReasonFactPacket
    ) -> PacketNarrativeResult:
        """Polish a minimal fact packet, rejecting the entire response on any breach."""
        if self._llm is None:
            return PacketNarrativeResult(None, "narration_unavailable", None)
        try:
            response = await self._llm.chat(
                [
                    ChatMessage(
                        role="system",
                        content="你是受事实包约束的医学推荐表述编辑器，只返回JSON。",
                    ),
                    ChatMessage(role="user", content=narration_prompt(packet)),
                ]
            )
            output, validation = validate_polished_reason(packet, response.text)
            return PacketNarrativeResult(
                output,
                validation.error_code,
                getattr(response, "model", None),
            )
        except TimeoutError:
            return PacketNarrativeResult(None, "narration_timeout", None)
        except Exception:
            logger.warning("Recommendation narration provider unavailable", exc_info=True)
            return PacketNarrativeResult(None, "narration_unavailable", None)

    async def render(
        self,
        *,
        citation: CitationItem,
        intent: dict[str, object],
        evidence: dict[str, object],
        fallback_headline: str,
        fallback_narrative: str,
    ) -> NarrativeResult:
        if not citation.abstract:
            return NarrativeResult(fallback_headline, fallback_narrative, None)
        if self._llm is None:
            return NarrativeResult(
                fallback_headline,
                fallback_narrative,
                "llm_narration_not_configured",
            )
        payload = {
            "intent": intent,
            "article": {"abstract": citation.abstract},
            "computed_evidence": evidence,
        }
        prompt = (
            "根据JSON中的结构化证据压缩成中文推荐定位与80至150字理由。"
            "只能复述输入事实，不得新增数字、疗效结论或因果结论；"
            "不得输出PMID、DOI、作者、题名、年份或期刊。"
            '只返回JSON：{"headline":"...","narrative":"..."}。\n'
            + json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )
        try:
            response = await self._llm.chat(
                [
                    ChatMessage(
                        role="system",
                        content="你是受证据约束的医学推荐理由编辑器。",
                    ),
                    ChatMessage(role="user", content=prompt),
                ]
            )
            parsed = self._parse_output(response.text)
            if not self._is_safe(parsed, citation, prompt):
                correction = (
                    prompt
                    + "\n上一次输出未通过事实校验。请不要复述文章题名、作者、期刊、年份或PMID，"
                    "不要新增数字或确定性疗效结论；仅返回符合格式的JSON。"
                )
                retry = await self._llm.chat(
                    [
                        ChatMessage(
                            role="system",
                            content="你是受证据约束的医学推荐理由编辑器。",
                        ),
                        ChatMessage(role="user", content=correction),
                    ]
                )
                parsed = self._parse_output(retry.text)
                if not self._is_safe(parsed, citation, prompt):
                    final_retry = await self._llm.chat(
                        [
                            ChatMessage(
                                role="system",
                                content="你是受证据约束的医学推荐理由编辑器。不得摘抄article字段中的题名、作者、期刊、年份或PMID。",
                            ),
                            ChatMessage(
                                role="user",
                                content=(
                                    correction
                                    + "\n这是最后一次改写：只概括研究意图匹配与待核验价值，不要复述article字段。"
                                ),
                            ),
                        ]
                    )
                    parsed = self._parse_output(final_retry.text)
                    if not self._is_safe(parsed, citation, prompt):
                        raise NarrationValidationError("narration_failed_fact_validation")
            return NarrativeResult(parsed.headline, parsed.narrative, None)
        except (NarrationValidationError, ValidationError):
            logger.warning("Recommendation narration did not pass fact validation")
            return NarrativeResult(
                fallback_headline,
                fallback_narrative,
                "llm_narration_rejected",
            )
        except (AttributeError, TypeError, ValueError):
            logger.warning(
                "Recommendation narration failed; deterministic text retained"
            )
            return NarrativeResult(
                fallback_headline,
                fallback_narrative,
                "llm_narration_unavailable",
            )
        except Exception:
            logger.warning(
                "Recommendation narration provider unavailable", exc_info=True
            )
            return NarrativeResult(
                fallback_headline,
                fallback_narrative,
                "llm_narration_unavailable",
            )

    @staticmethod
    def _parse_output(value: object) -> NarrationOutput:
        raw = str(value).strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
        return NarrationOutput.model_validate_json(raw)

    @staticmethod
    def _is_safe(output: NarrationOutput, citation: CitationItem, prompt: str) -> bool:
        rendered = f"{output.headline} {output.narrative}".casefold()
        forbidden = [
            citation.pmid,
            citation.doi,
            citation.title,
            citation.journal,
            citation.year and str(citation.year),
            *citation.authors,
        ]
        if any(value and str(value).casefold() in rendered for value in forbidden):
            return False
        if UNSUPPORTED_CERTAINTY_PATTERN.search(rendered):
            return False
        allowed_numbers = set(NUMBER_PATTERN.findall(prompt))
        return set(NUMBER_PATTERN.findall(rendered)) <= allowed_numbers
