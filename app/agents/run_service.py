"""持久化 Agent 运行与人工审批服务。"""

import re
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from pydantic import TypeAdapter
from typing_extensions import deprecated

from app.agents.adapter import AgentEvidenceAdapter, AgentEvidenceResult
from app.agents.legacy_adapter import LegacyRunAdapter
from app.agents.model import AgentRunRecord
from app.agents.repository import AgentRunRepository
from app.agents.state import AgentGraphState
from app.agents.trace import TraceEvent, create_event
from app.core.config import settings
from app.rag.numeric_verifier import verified_numeric_facts
from app.rag.schemas import EvidenceSet, GroundedAnswer, QueryPlan, RetrievalTrace
from app.rag.trace import TracePolicy, sanitize_trace


class AgentRunService:
    """旧 JSON Run 的兼容服务；不得作为 M0 正式交接链路使用。"""

    def __init__(
        self,
        *,
        repository: AgentRunRepository,
        adapter: AgentEvidenceAdapter | None = None,
        legacy_adapter: LegacyRunAdapter | None = None,
        allow_legacy_writes: bool = False,
    ) -> None:
        self._repository = repository
        self._adapter = adapter
        self._legacy_adapter = legacy_adapter or LegacyRunAdapter()
        self._allow_legacy_writes = allow_legacy_writes

    @deprecated("Use the M0 runtime; legacy writes are for historical tests only", category=None)
    def start(self, initial: AgentGraphState) -> tuple[str, AgentGraphState]:
        self._require_legacy_write_access()
        run_id = str(uuid4())
        state = self._initial_state(initial)
        events = [
            create_event(run_id, "graph_start", {"task_type": state["task_type"]}, {})
        ]
        if self._adapter is None:
            return run_id, self._finish(
                run_id, state, events, ["adapter_unavailable"], None
            )
        try:
            result = self._adapter.execute(state)
        except (RuntimeError, ValueError):
            return run_id, self._finish(run_id, state, events, ["adapter_failed"], None)
        state, trace = self._attach_result(state, result)
        events.append(
            create_event(
                run_id, "retrieve_evidence", {}, {"trace_id": result.trace.trace_id}
            )
        )
        errors = _validate_completion(result.evidence, result.answer)
        events.append(
            create_event(
                run_id,
                "evidence_check",
                {},
                {"errors": errors},
                trace_id=result.trace.trace_id,
                sources=_sources(result),
            )
        )
        if errors and errors != ["unresolved_evidence_conflicts"]:
            return run_id, self._finish(run_id, state, events, errors, trace)
        if _requires_approval(state, result.evidence):
            state["workflow_status"] = "awaiting_confirmation"
            state["approval_payload"] = _approval_payload(
                state, result.evidence, result.answer
            )
            events.append(
                create_event(
                    run_id,
                    "human_confirmation",
                    {},
                    state["approval_payload"],
                    trace_id=result.trace.trace_id,
                    sources=_sources(result),
                )
            )
            self._save(run_id, state, events, trace)
            return run_id, state
        return run_id, self._complete(run_id, state, events, trace, result)

    @deprecated("Use structured M0 confirmations", category=None)
    def resume(self, run_id: str, decision: str) -> AgentGraphState:
        self._require_legacy_write_access()
        record = self._require(run_id)
        state = TypeAdapter(AgentGraphState).validate_python(deepcopy(record.state_json))
        if state.get("workflow_status") != "awaiting_confirmation":
            raise ValueError("agent run is not awaiting confirmation")
        events = [TraceEvent.from_dict(item) for item in record.events_json]
        if decision in {"reject", "cancel"}:
            status = "rejected" if decision == "reject" else "cancelled"
            state.update({"workflow_status": status, "decision": status})
            events.append(
                create_event(
                    run_id,
                    "human_approval",
                    {"decision": decision},
                    {"status": status},
                    approval=decision,
                )
            )
            self._save(run_id, state, events, record.retrieval_trace_json)
            return state
        if decision != "approve":
            raise ValueError("invalid approval decision")
        result = _result_from_state(state)
        state.update(
            {
                "workflow_status": "running",
                "decision": "approved",
                "pending_confirmations": [],
            }
        )
        return self._complete(
            run_id,
            state,
            events,
            record.retrieval_trace_json,
            result,
            approval="approve",
        )

    def get(self, run_id: str) -> AgentGraphState:
        return TypeAdapter(AgentGraphState).validate_python(
            deepcopy(self._require(run_id).state_json)
        )

    def _require_legacy_write_access(self) -> None:
        if not self._allow_legacy_writes:
            raise RuntimeError("legacy_agent_run_writes_retired")

    def get_trace(self, run_id: str) -> list[TraceEvent]:
        return [
            TraceEvent.from_dict(item) for item in self._require(run_id).events_json
        ]

    def get_retrieval_trace(self, run_id: str) -> dict[str, object] | None:
        return deepcopy(self._require(run_id).retrieval_trace_json)

    def _complete(
        self,
        run_id: str,
        state: AgentGraphState,
        events: list[TraceEvent],
        trace: dict[str, object] | None,
        result: AgentEvidenceResult,
        approval: str | None = None,
    ) -> AgentGraphState:
        events.append(
            create_event(
                run_id,
                "citation_check",
                {},
                {"status": "validated"},
                trace_id=result.trace.trace_id,
                sources=_sources(result),
                approval=approval,
            )
        )
        state["workflow_status"] = "completed"
        events.append(
            create_event(
                run_id,
                "complete",
                {},
                {"status": "completed"},
                trace_id=result.trace.trace_id,
            )
        )
        self._save(run_id, state, events, trace)
        return state

    def _finish(
        self,
        run_id: str,
        state: AgentGraphState,
        events: list[TraceEvent],
        errors: list[str],
        trace: dict[str, object] | None,
    ) -> AgentGraphState:
        state["workflow_status"] = "failed"
        state["errors"] = errors
        events.append(create_event(run_id, "error", {}, {"errors": errors}))
        self._save(run_id, state, events, trace)
        return state

    def _save(
        self,
        run_id: str,
        state: AgentGraphState,
        events: list[TraceEvent],
        trace: dict[str, object] | None,
    ) -> None:
        stored = deepcopy(state)
        stored["user_query"] = "[not_persisted]"
        self._repository.save(
            AgentRunRecord(
                run_id=run_id,
                workflow_status=str(state["workflow_status"]),
                state_json=stored,
                events_json=[event.to_dict() for event in events],
                retrieval_trace_json=trace,
            )
        )

    def _require(self, run_id: str) -> AgentRunRecord:
        record = self._repository.get(run_id)
        if record is None:
            raise KeyError(run_id)
        self._legacy_adapter.read(record)
        return record

    @staticmethod
    def _initial_state(initial: AgentGraphState) -> AgentGraphState:
        return {
            "user_query": initial.get("user_query", ""),
            "task_type": initial.get("task_type", "evidence_qa"),
            "publish_requested": initial.get("publish_requested", False),
            "workflow_status": "running",
            "errors": [],
            "pending_confirmations": [],
            "approval_payload": {},
        }

    @staticmethod
    def _attach_result(
        state: AgentGraphState, result: AgentEvidenceResult
    ) -> tuple[AgentGraphState, dict[str, object]]:
        state["evidence"] = [
            item.model_dump(exclude={"text_original"})
            for item in result.evidence.evidence
        ]
        state["citations"] = [item.model_dump() for item in result.answer.citations]
        state["grounded_answer"] = result.answer.model_dump(exclude={"answer"})
        state["execution"] = {
            "evidence": result.evidence.model_dump(
                exclude={"evidence": {"__all__": {"text_original"}}}
            ),
            "answer": result.answer.model_dump(exclude={"answer"}),
            "trace_id": result.trace.trace_id,
        }
        trace = sanitize_trace(
            result.trace, TracePolicy(data_dir=Path(settings.DATA_DIR))
        ).model_dump(mode="json")
        return state, trace


def _validate_completion(evidence: EvidenceSet, answer: GroundedAnswer) -> list[str]:
    if evidence.status != "ready" or not evidence.evidence:
        return ["evidence_not_ready"]
    chunks = {item.chunk_id for item in evidence.evidence}
    evidence_by_chunk = {item.chunk_id: item for item in evidence.evidence}
    citations = {item.citation_id: item for item in answer.citations}
    verified = {
        item.source_chunk_id
        for item in verified_numeric_facts(evidence.numeric_facts, chunks)
    }
    if not answer.claims:
        return ["no_grounded_claims"]
    for claim in answer.claims:
        if (
            not claim.claim.strip()
            or not claim.evidence_chunk_ids
            or not set(claim.evidence_chunk_ids).issubset(chunks)
        ):
            return ["invalid_claim_evidence_binding"]
        if not claim.citation_ids or not set(claim.citation_ids).issubset(citations):
            return ["invalid_claim_citation_binding"]
        if any(
            citations[key].chunk_id not in claim.evidence_chunk_ids
            for key in claim.citation_ids
        ):
            return ["citation_not_bound_to_claim_evidence"]
        if any(
            citations[key].document_id
            != evidence_by_chunk[citations[key].chunk_id].document_id
            or citations[key].source_path
            != evidence_by_chunk[citations[key].chunk_id].source_path
            for key in claim.citation_ids
        ):
            return ["invalid_citation_provenance"]
        is_numeric_claim = claim.is_numeric or bool(re.search(r"\d", claim.claim))
        if is_numeric_claim and (
            not claim.is_numeric
            or not claim.numeric_fact_ids
            or not set(claim.numeric_fact_ids).issubset(verified)
        ):
            return ["unverified_numeric_claim"]
    return ["unresolved_evidence_conflicts"] if evidence.conflicts else []


def _requires_approval(state: AgentGraphState, evidence: EvidenceSet) -> bool:
    return (
        state.get("task_type") in {"writing", "research_direction"}
        or bool(state.get("publish_requested"))
        or bool(evidence.conflicts)
    )


def _approval_payload(
    state: AgentGraphState, evidence: EvidenceSet, answer: GroundedAnswer
) -> dict[str, object]:
    return {
        "task_type": state["task_type"],
        "evidence_status": evidence.status,
        "citations": [
            {
                "citation_id": item.citation_id,
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "page_number": item.page_number,
            }
            for item in answer.citations
        ],
        "limitations": answer.limitations
        + (["conflicting evidence"] if evidence.conflicts else []),
        "actions": ["approve", "reject", "cancel"],
    }


def _sources(result: AgentEvidenceResult) -> list[dict[str, object]]:
    return [
        {
            "document_id": item.document_id,
            "chunk_id": item.chunk_id,
            "source_path": Path(item.source_path).name,
            "page_number": item.page_number,
            "citation_id": item.chunk_id,
        }
        for item in result.evidence.evidence
    ]


def _result_from_state(state: AgentGraphState) -> AgentEvidenceResult:
    execution = state.get("execution")
    if not isinstance(execution, dict):
        raise ValueError("persisted execution contract missing")  # noqa: TRY004
    evidence_payload = deepcopy(execution["evidence"])
    if not isinstance(evidence_payload, dict):
        raise TypeError("persisted evidence must be an object")
    for item in evidence_payload.get("evidence", []):
        item["text_original"] = "[not_persisted]"
    evidence = EvidenceSet.model_validate(evidence_payload)
    answer_payload = deepcopy(execution["answer"])
    if not isinstance(answer_payload, dict):
        raise TypeError("persisted answer must be an object")
    answer_payload["answer"] = "[not_persisted]"
    answer = GroundedAnswer.model_validate(answer_payload)
    trace = RetrievalTrace(
        query_plan=QueryPlan(query="[not_persisted]"), trace_id=str(execution["trace_id"])
    )
    return AgentEvidenceResult(evidence=evidence, answer=answer, trace=trace)
