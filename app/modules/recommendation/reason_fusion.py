"""基于真实摘要的推荐理由融合，禁止模型产生论文元数据。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.integrations.llm.exceptions import LLMClientError
from app.integrations.llm.schemas import ChatMessage
from app.modules.literature_search.schema import CitationItem

_REASON_FALLBACK = "已通过 PubMed 元数据验证；该记录无摘要，未生成摘要依据推荐理由。"
_FAILURE_FALLBACK = "LLM理由生成失败，保留真实文献条目，未采用模型输出。"
_METADATA_FALLBACK = "LLM理由包含论文元数据，未采用模型输出。"


class ReasonLLM(Protocol):
    async def chat(self, messages: list[ChatMessage]): ...


@dataclass(frozen=True)
class RecommendationReasonItem:
    citation: CitationItem
    recommendation_reason: str


class RecommendationReasonService:
    """LLM只填写理由字段，论文元数据始终来自 CitationItem。"""

    def __init__(self, *, llm: ReasonLLM) -> None:
        self._llm = llm

    async def fuse(self, items: list[CitationItem]) -> list[RecommendationReasonItem]:
        results: list[RecommendationReasonItem] = []
        for item in items:
            reason = await self._reason_for(item)
            results.append(
                RecommendationReasonItem(citation=item, recommendation_reason=reason)
            )
        return results

    async def _reason_for(self, item: CitationItem) -> str:
        if not item.has_abstract or not item.abstract:
            return _REASON_FALLBACK
        prompt = (
            "仅根据下方摘要撰写一条简洁的中文推荐理由。"
            "摘要未提及的信息不得补充。不得输出PMID、DOI、题名、作者、年份或期刊。"
            "只返回理由正文，不要标题、列表编号或免责声明。\n\n"
            f"摘要：{item.abstract}"
        )
        try:
            response = await self._llm.chat(
                [
                    ChatMessage(
                        role="system",
                        content="你是医学文献摘要融合器，只能基于给定摘要陈述，不得编造事实。",
                    ),
                    ChatMessage(role="user", content=prompt),
                ]
            )
        except LLMClientError:
            return _FAILURE_FALLBACK
        reason = response.text.strip()
        if not reason or self._contains_metadata(reason, item):
            return _METADATA_FALLBACK
        return reason

    @staticmethod
    def _contains_metadata(reason: str, item: CitationItem) -> bool:
        lowered = reason.casefold()
        metadata = [item.pmid, item.doi, item.title, item.year and str(item.year)]
        if any(value and str(value).casefold() in lowered for value in metadata):
            return True
        for author in item.authors:
            tokens = re.findall(r"[A-Za-z]{3,}", author.casefold())
            if any(token in lowered for token in tokens):
                return True
        return False
