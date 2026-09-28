import pytest

from app.rag.answer_service import _validate_answer, generate_answer
from app.rag.exceptions import GroundedGenerationError, InvalidGeneratedAnswerError
from app.rag.schemas import (
    EvidenceConflict,
    EvidenceSet,
    GroundedAnswer,
    GroundedCitation,
    GroundedClaim,
    NumericFact,
    RankedEvidence,
)


class FakeGenerator:
    model_version = "fake-v1"

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls = 0

    def generate(self, evidence: EvidenceSet) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return "grounded answer"


def _evidence_set(**kwargs) -> EvidenceSet:
    return EvidenceSet(
        evidence=[
            RankedEvidence(
                document_id="domain-doc",
                chunk_id="chunk-1",
                source_path="source.pdf",
                text_original="verified evidence",
                rank=1,
            )
        ],
        **kwargs,
    )


def test_wp7_insufficient_evidence_skips_generator() -> None:
    generator = FakeGenerator()
    answer = generate_answer(EvidenceSet(status="insufficient_evidence"), generator)
    assert answer.evidence_status == "insufficient_evidence"
    assert generator.calls == 0


def test_wp7_generator_consumes_evidence_set_and_maps_ranked_evidence_citations() -> None:
    answer = generate_answer(_evidence_set(), FakeGenerator())
    assert answer.answer == "grounded answer"
    assert [(citation.document_id, citation.chunk_id) for citation in answer.citations] == [
        ("domain-doc", "chunk-1")
    ]


def test_wp7_conflicts_are_disclosed_and_generator_error_is_safe() -> None:
    evidence = _evidence_set(
        conflicts=[
            EvidenceConflict(metric="PFS", population="ITT", source_chunk_ids=["chunk-1"])
        ]
    )
    assert "冲突" in generate_answer(evidence, FakeGenerator()).limitations[0]
    failed = generate_answer(
        evidence, FakeGenerator(error=GroundedGenerationError("model failure"))
    )
    assert failed.evidence_status == "system_failure" and failed.fallback is True


def test_wp7_claim_validation_requires_known_citation_and_verified_numeric_fact() -> None:
    evidence = _evidence_set(
        numeric_facts=[
            NumericFact(
                metric="PFS",
                value="12",
                unit="months",
                population="ITT",
                source_chunk_id="chunk-1",
                verified=True,
            )
        ]
    )
    answer = GroundedAnswer(
        answer="PFS was 12 months.",
        claims=[
            GroundedClaim(
                claim="PFS was 12 months.",
                citation_ids=["chunk-1"],
                is_numeric=True,
                numeric_fact_ids=["chunk-1"],
            )
        ],
        citations=[
            GroundedCitation(
                citation_id="chunk-1",
                document_id="domain-doc",
                chunk_id="chunk-1",
                source_path="source.pdf",
            )
        ],
    )
    _validate_answer(answer, evidence)

    answer.claims[0].citation_ids = ["missing"]
    with pytest.raises(InvalidGeneratedAnswerError):
        _validate_answer(answer, evidence)

    answer.claims[0].citation_ids = ["chunk-1"]
    answer.claims[0].numeric_fact_ids = ["unverified"]
    with pytest.raises(InvalidGeneratedAnswerError):
        _validate_answer(answer, evidence)
