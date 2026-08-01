"""Explicit real-PDF PaperQA2 adapter integration test using local Ollama only."""

import json
import os
from pathlib import Path

import pytest

from app.core.config import Settings
from app.integrations.paperqa2 import PaperDocument, create_paperqa2_client

pytestmark = pytest.mark.integration

PDF_PATH = Path("data/paperqa2_r0/plos-medicine-carrs-followup.pdf")
QUESTION = (
    "How many cumulative first microvascular and macrovascular events occurred during "
    "6.5 years of observation, and how many were in the intervention and usual-care groups?"
)


@pytest.mark.skipif(
    os.getenv("RUN_PAPERQA2_TEST") != "1",
    reason="set RUN_PAPERQA2_TEST=1 to run the fixed local PaperQA2 integration",
)
@pytest.mark.asyncio
async def test_real_pdf_index_answer_sources_and_repeat_rule():
    assert PDF_PATH.is_file(), f"public test PDF is missing: {PDF_PATH}"
    client = create_paperqa2_client(
        Settings(
            OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        )
    )
    document = PaperDocument(
        path=PDF_PATH,
        title="CARRS randomized clinical trial follow-up",
        citation="PLOS Medicine (2023). doi:10.1371/journal.pmed.1004335",
    )

    first = await client.index_documents([document])
    repeated = await client.index_documents([document])
    answer = await client.ask(first, QUESTION)

    assert first.reused is False
    assert repeated.reused is True
    assert repeated.index_id == first.index_id
    assert answer.answer
    assert all(value in answer.answer for value in ("507", "233", "274"))
    assert answer.sources
    assert any(source.citation for source in answer.sources)
    print(json.dumps(answer.model_dump(mode="json"), ensure_ascii=True, indent=2))
