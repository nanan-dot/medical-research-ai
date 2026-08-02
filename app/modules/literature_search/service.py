"""Literature-search intent orchestration."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.integrations.llm.client import LLMClient
from app.integrations.llm.schemas import ChatMessage
from app.integrations.ollama.client import OllamaClient
from app.modules.literature_search.prompts import PROMPT_VERSION, build_candidate_prompt
from app.modules.literature_search.query_model import SearchIntentCandidate, relative_year_range
from app.modules.literature_search.repository import LiteratureSearchRepository
from app.modules.literature_search.schema import (
    BooleanQueryResult,
    ExpandTermsResponse,
    MeshCandidate,
    ParseQueryResponse,
    SearchTermGroup,
)
from app.modules.literature_search.mesh_client import MeshClient
from app.modules.literature_search.query_builder import build_boolean_query
from app.modules.literature_search.term_expansion import expand_term, is_ascii_search_term

CandidateExtractor = Callable[[str], Awaitable[str]]


class LiteratureSearchService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        candidate_extractor: CandidateExtractor | None = None,
        mesh_client: MeshClient | None = None,
    ):
        self.repo = LiteratureSearchRepository(session)
        self.candidate_extractor = candidate_extractor or self._extract_with_configured_model
        self.mesh_client = mesh_client or MeshClient()

    async def get(self, id: int):
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"LiteratureSearch not found: {id}")
        return entity

    async def list_records(self, offset: int = 0, limit: int = 20):
        return await self.repo.list(offset=offset, limit=limit)

    async def delete(self, id: int):
        entity = await self.get(id)
        await self.repo.delete(entity)
        return entity

    async def parse_query(self, raw_topic: str) -> ParseQueryResponse:
        normalized = " ".join(raw_topic.split())
        fallback = self._rule_candidate(normalized)
        try:
            raw_json = await self.candidate_extractor(build_candidate_prompt(normalized))
            candidate = self._constrain_candidate(
                SearchIntentCandidate.model_validate_json(raw_json), normalized
            )
            source = "model_candidate"
        except (ValueError, json.JSONDecodeError):
            candidate = fallback
            source = "rule_fallback"
        return ParseQueryResponse(
            raw_topic=raw_topic,
            candidate=candidate,
            clarification_questions=self._clarification_questions(candidate),
            candidate_source=source,
            prompt_version=PROMPT_VERSION,
        )

    async def expand_terms(
        self, candidate: SearchIntentCandidate, user_edits: dict[str, list[str]]
    ) -> ExpandTermsResponse:
        values = {
            "disease": candidate.disease,
            "intervention": candidate.intervention,
            "target": candidate.target,
            "mechanism": candidate.mechanism,
        }
        if not any(values.values()):
            values["topic"] = candidate.topic

        groups: list[SearchTermGroup] = []
        mesh_candidates: list[MeshCandidate] = []
        warnings: list[str] = []
        for name, value in values.items():
            if not value:
                continue
            expansion = expand_term(value)
            terms = list(dict.fromkeys([*expansion.synonyms, *user_edits.get(name, [])]))
            ascii_terms = [term for term in terms if is_ascii_search_term(term)]
            if len(ascii_terms) != len(terms):
                warnings.append(f"{name}: Chinese-only terms were retained for editing but omitted from PubMed query output.")
            if not ascii_terms:
                continue
            groups.append(
                SearchTermGroup(
                    name=name,
                    core_term=expansion.core_term,
                    terms=ascii_terms,
                    source=expansion.source,
                )
            )
            try:
                rows = await self.mesh_client.lookup(expansion.core_term)
            except Exception:
                warnings.append(f"{name}: official MeSH lookup was unavailable; no MeSH candidate was assumed.")
                continue
            mesh_candidates.extend(
                MeshCandidate(group_name=name, **row) for row in rows
            )
        return ExpandTermsResponse(
            term_groups=groups,
            mesh_candidates=mesh_candidates,
            warnings=warnings,
            user_edits=user_edits,
        )

    @staticmethod
    def build_query(groups: list[SearchTermGroup]) -> BooleanQueryResult:
        return build_boolean_query(groups)

    @staticmethod
    async def _extract_with_configured_model(prompt: str) -> str:
        from app.core.config import settings

        message = [ChatMessage(role="user", content=prompt)]
        if settings.DEFAULT_MODEL_PROVIDER == "ollama":
            async with OllamaClient.from_settings() as client:
                return (await client.chat(message)).text
        async with LLMClient.from_settings() as client:
            return (await client.chat(message)).text

    @staticmethod
    def _rule_candidate(raw_topic: str) -> SearchIntentCandidate:
        candidate = SearchIntentCandidate(topic=raw_topic)
        relative = re.search(r"近\s*([一二三四五六七八九十\d]{1,3})\s*年", raw_topic)
        if relative:
            candidate.date_range = relative_year_range(
                LiteratureSearchService._parse_year_count(relative.group(1)), relative.group(0)
            )
        return candidate

    @staticmethod
    def _constrain_candidate(candidate: SearchIntentCandidate, raw_topic: str) -> SearchIntentCandidate:
        if not candidate.topic.strip() or len(candidate.topic) > len(raw_topic) * 3:
            candidate.topic = raw_topic
        relative = re.search(r"近\s*([一二三四五六七八九十\d]{1,3})\s*年", raw_topic)
        if relative:
            candidate.date_range = relative_year_range(
                LiteratureSearchService._parse_year_count(relative.group(1)), relative.group(0)
            )
        return candidate

    @staticmethod
    def _parse_year_count(value: str) -> int:
        if value.isdigit():
            return int(value)
        numerals = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        }
        if value == "十":
            return 10
        if value.startswith("十"):
            return 10 + numerals[value[1]]
        if value.endswith("十"):
            return numerals[value[0]] * 10
        if "十" in value:
            return numerals[value[0]] * 10 + numerals[value[2]]
        return numerals[value]

    @staticmethod
    def _clarification_questions(candidate: SearchIntentCandidate) -> list[str]:
        questions: list[str] = []
        if not candidate.disease:
            questions.append("是否需要限定疾病或人群？")
        if not candidate.date_range:
            questions.append("需要限定发表时间范围吗？")
        if not candidate.study_types:
            questions.append("需要限定研究类型（如临床试验、综述或机制研究）吗？")
        return questions
