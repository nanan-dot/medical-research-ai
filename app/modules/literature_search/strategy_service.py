"""Domain operations for mutable strategy drafts and immutable snapshots."""

import json
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.exceptions import PubMedError
from app.modules.literature_search.mesh_client import MeshClient
from app.modules.literature_search.schema import LiteratureSearchTaskCreate
from app.modules.literature_search.service import LiteratureSearchService
from app.modules.literature_search.strategy_fingerprint import strategy_fingerprint
from app.modules.literature_search.strategy_model import (
    SearchStrategyDraft,
    SearchStrategyMeshTerm,
    SearchStrategyTerm,
    SearchStrategyVersion,
)
from app.modules.literature_search.strategy_schema import (
    StrategyCreate,
    StrategyMeshPatch,
    StrategyMeshRead,
    StrategyPatch,
    StrategyRead,
    StrategyTermCreate,
    StrategyTermPatch,
    StrategyTermRead,
    StrategyVersionRead,
)
from app.modules.literature_search.term_expansion import (
    expand_term,
    is_ascii_search_term,
)


class SearchStrategyService:
    """Own strategy persistence, stale propagation and version snapshots."""

    def __init__(
        self,
        session: AsyncSession,
        pubmed_client: PubMedClient | None = None,
        mesh_client: MeshClient | None = None,
    ) -> None:
        self._session = session
        self._pubmed_client = pubmed_client or PubMedClient.from_settings()
        self._mesh_client = mesh_client or MeshClient()

    async def create(self, request: StrategyCreate) -> StrategyRead:
        snapshot = self._snapshot_from_request(request)
        entity = SearchStrategyDraft(
            research_question=request.research_question,
            intent_mode=request.intent_mode,
            intent_json=self._dump(request.intent),
            limits_json=self._dump(request.limits),
            query_text=request.query_text,
            fingerprint=strategy_fingerprint(snapshot),
        )
        self._session.add(entity)
        await self._session.flush()
        # The entry pipeline has already completed expansion and NLM mapping.
        # Persist that exact snapshot atomically with the draft so a reload cannot
        # degrade a completed PICO strategy into an empty workspace.
        for position, term_request in enumerate(request.terms, start=1):
            text = term_request.text.strip()
            self._session.add(
                SearchStrategyTerm(
                    strategy_id=entity.id,
                    concept_group=term_request.concept_group,
                    text=text,
                    normalized_text=" ".join(text.lower().split()),
                    source=term_request.source,
                    field_tag=term_request.field_tag,
                    relation_type=term_request.relation_type,
                    is_locked=term_request.is_locked,
                    position=position,
                )
            )
        for mesh_request in request.mesh_terms:
            self._session.add(
                SearchStrategyMeshTerm(
                    strategy_id=entity.id,
                    descriptor=mesh_request.descriptor,
                    mesh_id=mesh_request.mesh_id,
                    concept_group=mesh_request.concept_group,
                    source=mesh_request.source,
                    verification_status=mesh_request.verification_status,
                    is_locked=mesh_request.is_locked,
                    verification_checked_at=datetime.now(UTC),
                )
            )
        await self._session.flush()
        entity.fingerprint = strategy_fingerprint(
            self._snapshot(entity, await self._terms(entity.id))
        )
        await self._session.flush()
        return await self._read(entity)

    async def get(self, strategy_id: int) -> StrategyRead:
        return await self._read(await self._entity(strategy_id))

    async def latest_complete(self) -> StrategyRead:
        """Return the newest strategy that can render the complete PICO workspace."""
        result = await self._session.scalars(
            select(SearchStrategyDraft)
            .where(
                SearchStrategyDraft.intent_mode == "pico",
                SearchStrategyDraft.query_text != "",
            )
            .order_by(SearchStrategyDraft.id.desc())
        )
        for entity in result:
            terms = await self._terms(entity.id)
            concept_groups = {term.concept_group for term in terms}
            if {"disease", "intervention", "outcome"}.issubset(concept_groups):
                return await self._read(entity)
        raise HTTPException(status_code=404, detail="尚无完整的 PICO 检索策略。")

    async def patch(self, strategy_id: int, request: StrategyPatch) -> StrategyRead:
        entity = await self._entity(strategy_id)
        if entity.revision != request.revision:
            raise HTTPException(status_code=409, detail="策略已被更新，请刷新后再保存。")
        if request.research_question is not None:
            entity.research_question = request.research_question
        if request.intent_mode is not None:
            entity.intent_mode = request.intent_mode
        if request.intent is not None:
            entity.intent_json = self._dump(request.intent)
        if request.limits is not None:
            entity.limits_json = self._dump(request.limits)
        if request.query_text is not None:
            entity.query_text = request.query_text
        if request.query_source is not None:
            entity.query_source = request.query_source
        entity.revision += 1
        entity.fingerprint = strategy_fingerprint(
            self._snapshot(entity, await self._terms(strategy_id))
        )
        # Save has succeeded, but dependent external validation/count is no longer current.
        entity.validation_state = "stale"
        entity.count_state = "stale"
        entity.last_saved_at = datetime.now(UTC)
        await self._session.flush()
        return await self._read(entity)

    async def add_term(self, strategy_id: int, request: StrategyTermCreate) -> StrategyTermRead:
        entity = await self._entity(strategy_id)
        position = await self._next_term_position(strategy_id)
        term = SearchStrategyTerm(
            strategy_id=strategy_id,
            concept_group=request.concept_group,
            text=request.text.strip(),
            normalized_text=" ".join(request.text.lower().split()),
            source=request.source,
            field_tag=request.field_tag,
            relation_type=request.relation_type,
            is_locked=request.is_locked,
            position=position,
        )
        self._session.add(term)
        await self._touch_downstream(entity)
        await self._session.flush()
        return self._term_read(term)

    async def patch_term(self, strategy_id: int, term_id: int, request: StrategyTermPatch) -> StrategyTermRead:
        entity = await self._entity(strategy_id)
        term = await self._term(strategy_id, term_id)
        if request.is_locked is not None:
            term.is_locked = request.is_locked
        if request.text is not None:
            term.text = request.text.strip()
            term.normalized_text = " ".join(request.text.lower().split())
        await self._touch_downstream(entity)
        await self._session.flush()
        return self._term_read(term)

    async def delete_term(self, strategy_id: int, term_id: int) -> None:
        entity = await self._entity(strategy_id)
        term = await self._term(strategy_id, term_id)
        await self._session.delete(term)
        await self._touch_downstream(entity)

    async def remap_terms(self, strategy_id: int) -> dict[str, Any]:
        entity = await self._entity(strategy_id)
        intent = self._load(entity.intent_json)
        remapped: list[tuple[str, str]] = []
        for concept_group in ("disease", "intervention", "comparison", "outcome"):
            value = intent.get(concept_group)
            if not isinstance(value, str) or not value.strip():
                continue
            expansion = expand_term(value)
            remapped.extend(
                (concept_group, term)
                for term in expansion.synonyms
                if is_ascii_search_term(term)
            )

        if not remapped:
            retained = await self._terms(strategy_id)
            if not retained:
                raise HTTPException(status_code=422, detail="当前研究意图没有可重新映射的英文术语。")
            read = await self._read(entity)
            return {
                "revision": read.revision,
                "fingerprint": read.fingerprint,
                "terms": [term.model_dump() for term in read.terms],
            }

        # 先计算完整替换结果，再删除旧自动术语，避免外部映射为空时破坏现有策略。
        await self._session.execute(
            delete(SearchStrategyTerm).where(
                SearchStrategyTerm.strategy_id == strategy_id,
                SearchStrategyTerm.source == "smart_expansion",
                SearchStrategyTerm.is_locked.is_(False),
            )
        )
        retained = await self._terms(strategy_id)
        normalized_retained = {term.normalized_text for term in retained}
        position = max((term.position for term in retained), default=0)
        for concept_group, text in remapped:
            normalized = " ".join(text.lower().split())
            if normalized in normalized_retained:
                continue
            position += 1
            normalized_retained.add(normalized)
            self._session.add(
                SearchStrategyTerm(
                    strategy_id=strategy_id,
                    concept_group=concept_group,
                    text=text,
                    normalized_text=normalized,
                    source="smart_expansion",
                    field_tag="Title/Abstract",
                    relation_type="synonym",
                    is_locked=False,
                    position=position,
                )
            )
        await self._session.flush()
        entity.revision += 1
        entity.fingerprint = strategy_fingerprint(
            self._snapshot(entity, await self._terms(strategy_id))
        )
        entity.validation_state = "stale"
        entity.count_state = "stale"
        entity.last_saved_at = datetime.now(UTC)
        await self._session.flush()
        read = await self._read(entity)
        return {"revision": read.revision, "fingerprint": read.fingerprint, "terms": [term.model_dump() for term in read.terms]}

    async def refresh_mesh(self, strategy_id: int) -> StrategyRead:
        """Refresh NLM evidence without letting an upstream failure erase the draft."""
        entity = await self._entity(strategy_id)
        terms = await self._terms(strategy_id)
        await self._session.execute(
            delete(SearchStrategyMeshTerm).where(
                SearchStrategyMeshTerm.strategy_id == strategy_id,
                SearchStrategyMeshTerm.is_locked.is_(False),
            )
        )
        checked_at = datetime.now(UTC)
        for concept_group, descriptor in self._mesh_refresh_targets(entity, terms):
            try:
                candidates = await self._mesh_client.lookup(descriptor)
            except (OSError, httpx.HTTPError):
                self._session.add(
                    SearchStrategyMeshTerm(
                        strategy_id=strategy_id,
                        descriptor=descriptor,
                        mesh_id=None,
                        concept_group=concept_group,
                        verification_status="unavailable",
                        verification_checked_at=checked_at,
                    )
                )
                continue
            if not candidates:
                self._session.add(
                    SearchStrategyMeshTerm(
                        strategy_id=strategy_id,
                        descriptor=descriptor,
                        mesh_id=None,
                        concept_group=concept_group,
                        verification_status="not_found",
                        verification_checked_at=checked_at,
                    )
                )
                continue
            for candidate in candidates:
                self._session.add(
                    SearchStrategyMeshTerm(
                        strategy_id=strategy_id,
                        descriptor=candidate["descriptor"],
                        mesh_id=candidate["mesh_id"],
                        concept_group=concept_group,
                        verification_status="verified",
                        verification_checked_at=checked_at,
                    )
                )
        entity.revision += 1
        entity.fingerprint = strategy_fingerprint(self._snapshot(entity, terms))
        entity.validation_state = "stale"
        entity.count_state = "stale"
        entity.last_saved_at = checked_at
        await self._session.flush()
        return await self._read(entity)

    def _mesh_refresh_targets(
        self,
        entity: SearchStrategyDraft,
        terms: list[SearchStrategyTerm],
    ) -> list[tuple[str, str]]:
        """Choose one auditable canonical descriptor per concept group."""
        intent = self._load(entity.intent_json)
        targets: list[tuple[str, str]] = []
        selected_groups: set[str] = set()
        for concept_group in (
            "disease",
            "intervention",
            "comparison",
            "outcome",
            "target",
            "mechanism",
        ):
            value = intent.get(concept_group)
            if not isinstance(value, str) or not value.strip():
                continue
            descriptor = expand_term(value).core_term
            if is_ascii_search_term(descriptor):
                targets.append((concept_group, descriptor))
                selected_groups.add(concept_group)
        for term in terms:
            if term.concept_group in selected_groups or not is_ascii_search_term(term.text):
                continue
            targets.append((term.concept_group, term.text))
            selected_groups.add(term.concept_group)
        return targets

    async def patch_mesh(
        self,
        strategy_id: int,
        mesh_term_id: int,
        request: StrategyMeshPatch,
    ) -> StrategyMeshRead:
        """Persist the user's lock state without asserting a different MeSH provenance."""
        entity = await self._entity(strategy_id)
        term = await self._session.get(SearchStrategyMeshTerm, mesh_term_id)
        if term is None or term.strategy_id != strategy_id:
            raise HTTPException(status_code=404, detail="未找到 MeSH 术语。")
        term.is_locked = request.is_locked
        await self._touch_downstream(entity)
        await self._session.flush()
        return self._mesh_read(term)

    async def create_version(self, strategy_id: int, note: str | None = None) -> SearchStrategyVersion:
        entity = await self._entity(strategy_id)
        latest = await self._session.scalar(select(SearchStrategyVersion).where(SearchStrategyVersion.strategy_id == strategy_id).order_by(SearchStrategyVersion.version.desc()).limit(1))
        if latest is not None and latest.fingerprint == entity.fingerprint:
            return latest
        next_version = 1 if latest is None else latest.version + 1
        version = SearchStrategyVersion(strategy_id=strategy_id, version=next_version, snapshot_json=self._dump(self._snapshot(entity, await self._terms(strategy_id))), fingerprint=entity.fingerprint, note=note)
        self._session.add(version)
        await self._session.flush()
        return version

    async def list_versions(self, strategy_id: int) -> list[SearchStrategyVersion]:
        await self._entity(strategy_id)
        result = await self._session.scalars(select(SearchStrategyVersion).where(SearchStrategyVersion.strategy_id == strategy_id).order_by(SearchStrategyVersion.version.desc()))
        return list(result)

    async def compare_versions(self, strategy_id: int, from_version: int, to_version: int) -> dict[str, Any]:
        """Return structured field-level changes between immutable strategy snapshots."""
        versions = await self.list_versions(strategy_id)
        indexed = {version.version: version for version in versions}
        if from_version not in indexed or to_version not in indexed:
            raise HTTPException(status_code=404, detail="未找到要比较的策略版本。")
        before = self._load(indexed[from_version].snapshot_json)
        after = self._load(indexed[to_version].snapshot_json)
        return {"from_version": from_version, "to_version": to_version, "changes": {key: {"from": before.get(key), "to": after.get(key)} for key in ("research_question", "intent_mode", "intent", "terms", "query_text", "limits") if before.get(key) != after.get(key)}}

    async def execute(self, strategy_id: int) -> Any:
        """Execute the current persisted fingerprint through the existing task subsystem."""
        validation = await self.validate(strategy_id)
        if validation["blocking_errors"]:
            raise HTTPException(status_code=400, detail="策略存在阻断性问题，不能开始检索。")
        entity = await self._entity(strategy_id)
        return await LiteratureSearchService(self._session).create_task(
            LiteratureSearchTaskCreate(
                original_query=entity.research_question,
                structured_query=entity.intent_json,
                search_string=entity.query_text,
                filters=entity.limits_json,
                model_version="strategy-workspace",
                user_edits=self._dump({"strategy_id": strategy_id, "strategy_fingerprint": entity.fingerprint}),
            )
        )

    async def validate(self, strategy_id: int) -> dict[str, Any]:
        entity = await self._entity(strategy_id)
        query = entity.query_text.strip()
        blocking_errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        if not query:
            blocking_errors.append({"code": "query_required", "message": "需要 PubMed 检索式后才能验证。", "severity": "blocking"})
        if query.count("(") != query.count(")"):
            blocking_errors.append({"code": "unbalanced_parentheses", "message": "检索式括号不匹配。", "severity": "blocking"})
        allowed_field_tags = {
            "ad",
            "affiliation",
            "au",
            "author",
            "dp",
            "la",
            "mesh",
            "mesh terms",
            "mh",
            "pmid",
            "pt",
            "publication type",
            "ta",
            "ti",
            "tiab",
            "title",
            "title/abstract",
            "tw",
        }
        invalid_tags = sorted(
            {
                tag.strip().lower()
                for tag in re.findall(r"\[([^\]]+)\]", query)
                if tag.strip().lower() not in allowed_field_tags
            }
        )
        if invalid_tags:
            blocking_errors.append(
                {
                    "code": "unsupported_field_tag",
                    "message": f"不支持的 PubMed 字段标签：{', '.join(invalid_tags)}。",
                    "severity": "blocking",
                }
            )
        mesh_terms = await self._session.scalars(
            select(SearchStrategyMeshTerm).where(
                SearchStrategyMeshTerm.strategy_id == strategy_id
            )
        )
        mesh_statuses = {term.verification_status for term in mesh_terms}
        mesh_valid = not ({"stale", "unavailable"} & mesh_statuses)
        if "unavailable" in mesh_statuses:
            warnings.append({"code": "mesh_unavailable", "message": "部分 NLM MeSH 状态不可用，请稍后刷新。", "severity": "warning"})
        if "stale" in mesh_statuses:
            warnings.append({"code": "mesh_stale", "message": "MeSH 映射已过期，请刷新后再确认。", "severity": "warning"})
        syntax_valid = not any(error["code"] in {"query_required", "unbalanced_parentheses"} for error in blocking_errors)
        field_tags_valid = not invalid_tags
        entity.validation_state = "valid" if not blocking_errors and mesh_valid else "invalid"
        await self._session.flush()
        return {"is_syntax_valid": syntax_valid, "is_mesh_valid": mesh_valid, "are_field_tags_valid": field_tags_valid, "warnings": warnings, "blocking_errors": blocking_errors, "validated_fingerprint": entity.fingerprint, "validated_at": datetime.now(UTC)}

    async def count(self, strategy_id: int, fingerprint: str) -> dict[str, Any]:
        entity = await self._entity(strategy_id)
        if fingerprint != entity.fingerprint:
            raise HTTPException(status_code=409, detail="策略已更新，已丢弃过期 Count 请求。")
        if not entity.query_text.strip():
            raise HTTPException(status_code=400, detail="需要有效检索式后才能获取 PubMed 匹配数量。")
        try:
            search = await self._pubmed_client.search(entity.query_text, retmax=1)
        except PubMedError:
            # Keep the prior verified count untouched: an external failure is not
            # evidence that the strategy matches zero records.
            entity.count_state = "failed"
            await self._session.flush()
            raise
        # A user may edit the strategy while PubMed is in flight. Re-read rather
        # than attaching an obsolete count to the newer fingerprint.
        current = await self._session.get(
            SearchStrategyDraft,
            strategy_id,
            populate_existing=True,
        )
        if current is None or current.fingerprint != fingerprint:
            raise HTTPException(status_code=409, detail="策略已更新，已丢弃过期 Count 响应。")
        retrieved_at = datetime.now(UTC)
        count = {"count": search.total_count, "fingerprint": current.fingerprint, "retrieved_at": retrieved_at.isoformat(), "source": "pubmed"}
        current.count_json = self._dump(count)
        current.count_state = "success"
        await self._session.flush()
        return count

    async def _touch_downstream(self, entity: SearchStrategyDraft) -> None:
        entity.revision += 1
        entity.fingerprint = strategy_fingerprint(self._snapshot(entity, await self._terms(entity.id)))
        entity.validation_state = "stale"
        entity.count_state = "stale"
        entity.last_saved_at = datetime.now(UTC)

    async def _entity(self, strategy_id: int) -> SearchStrategyDraft:
        entity = await self._session.get(SearchStrategyDraft, strategy_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="未找到检索策略。")
        return entity

    async def _term(self, strategy_id: int, term_id: int) -> SearchStrategyTerm:
        term = await self._session.get(SearchStrategyTerm, term_id)
        if term is None or term.strategy_id != strategy_id:
            raise HTTPException(status_code=404, detail="未找到检索术语。")
        return term

    async def _terms(self, strategy_id: int) -> list[SearchStrategyTerm]:
        result = await self._session.scalars(select(SearchStrategyTerm).where(SearchStrategyTerm.strategy_id == strategy_id).order_by(SearchStrategyTerm.position, SearchStrategyTerm.id))
        return list(result)

    async def _next_term_position(self, strategy_id: int) -> int:
        highest = await self._session.scalar(select(func.max(SearchStrategyTerm.position)).where(SearchStrategyTerm.strategy_id == strategy_id))
        return int(highest or 0) + 1

    async def _read(self, entity: SearchStrategyDraft) -> StrategyRead:
        terms = await self._terms(entity.id)
        mesh = await self._session.scalars(select(SearchStrategyMeshTerm).where(SearchStrategyMeshTerm.strategy_id == entity.id))
        return StrategyRead(id=entity.id, research_question=entity.research_question, intent_mode=entity.intent_mode, intent=self._load(entity.intent_json), limits=self._load(entity.limits_json), query_text=entity.query_text, query_source=entity.query_source, fingerprint=entity.fingerprint, revision=entity.revision, generation_state=entity.generation_state, validation_state=entity.validation_state, count_state=entity.count_state, count=self._load(entity.count_json), last_saved_at=entity.last_saved_at, terms=[self._term_read(term) for term in terms], mesh_terms=[self._mesh_read(row) for row in mesh])

    @staticmethod
    def _term_read(term: SearchStrategyTerm) -> StrategyTermRead:
        warning = None if term.warning_code is None else {"code": term.warning_code, "message": term.warning_detail or "需要确认此术语。", "severity": "warning"}
        return StrategyTermRead(id=term.id, concept_group=term.concept_group, text=term.text, source=term.source, field_tag=term.field_tag, relation_type=term.relation_type, is_locked=term.is_locked, warning=warning)

    @staticmethod
    def _mesh_read(term: SearchStrategyMeshTerm) -> StrategyMeshRead:
        return StrategyMeshRead(
            id=term.id,
            descriptor=term.descriptor,
            mesh_id=term.mesh_id,
            concept_group=term.concept_group,
            source=term.source,
            verification_status=term.verification_status,
            is_locked=term.is_locked,
            verification_checked_at=term.verification_checked_at,
        )

    @staticmethod
    def _dump(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

    @staticmethod
    def _load(value: str) -> dict[str, object]:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}

    def _snapshot_from_request(self, request: StrategyCreate) -> dict[str, Any]:
        return {
            "research_question": request.research_question,
            "intent_mode": request.intent_mode,
            "intent": request.intent,
            "limits": request.limits,
            "query_text": request.query_text,
            "terms": [
                {
                    "text": " ".join(term.text.lower().split()),
                    "group": term.concept_group,
                    "source": term.source,
                    "locked": term.is_locked,
                }
                for term in request.terms
            ],
        }

    def _snapshot(self, entity: SearchStrategyDraft, terms: list[SearchStrategyTerm]) -> dict[str, Any]:
        return {"research_question": entity.research_question, "intent_mode": entity.intent_mode, "intent": self._load(entity.intent_json), "limits": self._load(entity.limits_json), "query_text": entity.query_text, "terms": [{"text": term.normalized_text, "group": term.concept_group, "source": term.source, "locked": term.is_locked} for term in terms]}


def version_read(version: SearchStrategyVersion) -> StrategyVersionRead:
    """Convert immutable ORM snapshot metadata to its public contract."""
    return StrategyVersionRead(id=version.id, strategy_id=version.strategy_id, version=version.version, fingerprint=version.fingerprint, note=version.note, created_at=version.created_at)
