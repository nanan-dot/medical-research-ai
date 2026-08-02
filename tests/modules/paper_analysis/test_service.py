import json
from pathlib import Path

import pytest

from app.common.exceptions import ConflictError
from app.integrations.paperqa2 import PaperQAAnswer, PaperSource
from app.integrations.paperqa2.exceptions import PaperQA2OperationError
from app.modules.paper_analysis.prompts import FIELD_NAMES
from app.modules.paper_analysis.schema import AnalysisStatus, ClaimKind, PaperAnalysisCorrection
from app.modules.paper_analysis.service import PaperAnalysisService
from tests.modules.document.conftest import create_document


def result_payload(*, bad_source: bool = False):
    payload = {
        name: {"value": "未找到", "kind": "not_found", "source_indices": []}
        for name in FIELD_NAMES
    }
    payload["sample_size"] = {"value": "120 participants", "kind": "fact", "source_indices": [0]}
    payload["study_type"] = {"value": "randomized trial", "kind": "fact", "source_indices": [0]}
    payload["statistical_methods"] = {"value": "Cox regression", "kind": "fact", "source_indices": [0]}
    payload["main_results"] = {"value": "HR 0.80 (95% CI 0.70–0.91)", "kind": "fact", "source_indices": [2 if bad_source else 0]}
    return payload


class FakeClient:
    def __init__(self, *, bad_source: bool = False, fail: bool = False):
        self.bad_source = bad_source
        self.fail = fail
        self.questions = []

    async def ask(self, index, question):
        self.questions.append(question)
        if self.fail:
            raise PaperQA2OperationError("local analysis unavailable")
        return PaperQAAnswer(
            answer=json.dumps(result_payload(bad_source=self.bad_source)),
            index_id=index.index_id,
            sources=[PaperSource(citation="Trial report", page_start=4, page_end=5)],
        )


async def indexed_document(session, tmp_path: Path):
    document, _ = await create_document(session, tmp_path / "papers", "paper.pdf")
    document.index_status = "succeeded"
    document.paperqa_index_key = "idx-paper"
    document.paperqa_version = "2026.3.18"
    await session.commit()
    return document


@pytest.mark.asyncio
async def test_structured_analysis_extracts_methods_results_and_sources(session, tmp_path: Path):
    document = await indexed_document(session, tmp_path)
    client = FakeClient()
    analysis = await PaperAnalysisService(session, client_factory=lambda: client).create(document.id)

    assert analysis.analysis_status == AnalysisStatus.SUCCEEDED
    assert analysis.structured_result.sample_size.value == "120 participants"
    assert analysis.structured_result.study_type.value == "randomized trial"
    assert analysis.structured_result.statistical_methods.value == "Cox regression"
    assert "95% CI" in analysis.structured_result.main_results.value
    assert analysis.structured_result.main_results.source_indices == [0]
    assert analysis.sources[0].page_start == 4
    assert analysis.structured_result.population.kind == ClaimKind.NOT_FOUND
    assert "population" in analysis.pending_confirmations
    assert "Never invent" in client.questions[0]


@pytest.mark.asyncio
async def test_source_mismatch_sets_failed_status(session, tmp_path: Path):
    document = await indexed_document(session, tmp_path)
    service = PaperAnalysisService(session, client_factory=lambda: FakeClient(bad_source=True))
    with pytest.raises(ConflictError, match="failed"):
        await service.create(document.id)
    entity = await service.repo.latest_for_document(document.id)
    assert entity.analysis_status == AnalysisStatus.FAILED.value
    assert entity.error_code == "analysis_response_invalid"


@pytest.mark.asyncio
async def test_regenerate_increments_version_and_correction_is_saved(session, tmp_path: Path):
    document = await indexed_document(session, tmp_path)
    service = PaperAnalysisService(session, client_factory=FakeClient)
    created = await service.create(document.id)
    regenerated = await service.regenerate(created.id)
    assert regenerated.generation == 2

    corrected = await service.correct(
        created.id,
        PaperAnalysisCorrection(
            field_name="population", value="Adults", kind="summary", source_indices=[0]
        ),
    )
    assert corrected.structured_result.population.value == "Adults"
    assert "population" not in corrected.pending_confirmations


@pytest.mark.asyncio
async def test_markdown_export_preserves_key_number_and_reference(session, tmp_path: Path):
    document = await indexed_document(session, tmp_path)
    service = PaperAnalysisService(session, client_factory=FakeClient)
    created = await service.create(document.id)
    markdown = await service.export_markdown(created.id)
    assert "120 participants" in markdown
    assert "来源 1" in markdown
    assert "Trial report" in markdown


@pytest.mark.asyncio
async def test_external_failure_is_persisted_without_response_content(session, tmp_path: Path):
    document = await indexed_document(session, tmp_path)
    service = PaperAnalysisService(session, client_factory=lambda: FakeClient(fail=True))
    with pytest.raises(ConflictError):
        await service.create(document.id)
    entity = await service.repo.latest_for_document(document.id)
    assert entity.analysis_status == AnalysisStatus.FAILED.value
    assert entity.error_code == "paperqa2_operation_error"
