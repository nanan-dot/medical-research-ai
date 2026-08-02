"""Unit tests for the R0 PaperQA command-line workflow."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli.r0_demo import DemoError, DemoResult, build_parser, main, run_demo
from app.integrations.paperqa2.schemas import PaperQAAnswer, PaperQAIndex, PaperSource


class FakeClient:
    def __init__(self, *, answer=None, reused=False):
        self.answer = answer or PaperQAAnswer(
            answer="507 total: 233 intervention and 274 usual care.",
            index_id="pqa2-test",
            sources=[PaperSource(citation="Real citation", page_start=11, page_end=12)],
        )
        self.reused = reused
        self.documents = None
        self.question = None
        self.rebuild = None

    async def index_documents(self, documents, *, rebuild=False):
        self.documents = documents
        self.rebuild = rebuild
        return PaperQAIndex(index_id="pqa2-test", document_count=1, reused=self.reused)

    async def ask(self, index, question):
        self.question = question
        return self.answer


def make_pdf(tmp_path: Path, name: str = "paper with spaces.pdf") -> Path:
    path = tmp_path / name
    path.write_bytes(b"%PDF-test")
    return path


@pytest.mark.asyncio
async def test_correct_call_printable_result_and_json_write(tmp_path: Path):
    pdf = make_pdf(tmp_path)
    output = tmp_path / "nested" / "result.json"
    client = FakeClient()

    result = await run_demo(
        client=client,
        pdf_path=pdf,
        question="  What happened?  ",
        provider="ollama",
        model="qwen3:4b",
        output_path=output,
    )

    assert client.documents[0].path == pdf.resolve()
    assert client.question == "What happened?"
    assert client.rebuild is False
    assert result.answer.sources[0].page_start == 11
    saved = DemoResult.model_validate_json(output.read_text(encoding="utf-8"))
    assert saved == result


def test_required_arguments_are_enforced():
    with pytest.raises(SystemExit) as captured:
        build_parser().parse_args([])
    assert captured.value.code == 2


@pytest.mark.asyncio
async def test_missing_path_and_empty_question_are_input_errors(tmp_path: Path):
    with pytest.raises(DemoError, match="does not exist") as missing:
        await run_demo(
            client=FakeClient(),
            pdf_path=tmp_path / "missing.pdf",
            question="Question",
            provider="ollama",
            model="qwen3:4b",
            output_path=tmp_path / "result.json",
        )
    assert missing.value.exit_code == 2

    pdf = make_pdf(tmp_path)
    with pytest.raises(DemoError, match="must not be empty"):
        await run_demo(
            client=FakeClient(),
            pdf_path=pdf,
            question="   ",
            provider="ollama",
            model="qwen3:4b",
            output_path=tmp_path / "result.json",
        )


@pytest.mark.asyncio
async def test_empty_answer_is_rejected(tmp_path: Path):
    pdf = make_pdf(tmp_path)
    empty = SimpleNamespace(answer="", sources=[], index_id="pqa2-test")
    with pytest.raises(DemoError, match="empty answer"):
        await run_demo(
            client=FakeClient(answer=empty),
            pdf_path=pdf,
            question="Question",
            provider="ollama",
            model="qwen3:4b",
            output_path=tmp_path / "result.json",
        )


@pytest.mark.asyncio
async def test_unwritable_output_is_explicit(tmp_path: Path):
    pdf = make_pdf(tmp_path)
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("file", encoding="utf-8")

    with pytest.raises(DemoError, match="not writable") as captured:
        await run_demo(
            client=FakeClient(),
            pdf_path=pdf,
            question="Question",
            provider="ollama",
            model="qwen3:4b",
            output_path=blocked_parent / "result.json",
        )
    assert captured.value.exit_code == 3


@pytest.mark.asyncio
async def test_slow_reused_index_is_rejected(tmp_path: Path, monkeypatch):
    pdf = make_pdf(tmp_path)
    times = iter((0.0, 0.0, 6.0))
    monkeypatch.setattr("app.cli.r0_demo.perf_counter", lambda: next(times))

    with pytest.raises(DemoError, match="Reused index exceeded"):
        await run_demo(
            client=FakeClient(reused=True),
            pdf_path=pdf,
            question="Question",
            provider="ollama",
            model="qwen3:4b",
            output_path=tmp_path / "result.json",
            max_reuse_seconds=5.0,
        )


@pytest.mark.asyncio
async def test_cloud_and_local_results_have_identical_structure(tmp_path: Path):
    pdf = make_pdf(tmp_path)
    results = []
    for provider, model in (("ollama", "qwen3:4b"), ("openai", "cloud-model")):
        results.append(
            await run_demo(
                client=FakeClient(),
                pdf_path=pdf,
                question="Question",
                provider=provider,
                model=model,
                output_path=tmp_path / f"{provider}.json",
            )
        )

    assert set(results[0].model_dump()) == set(results[1].model_dump())
    assert set(results[0].answer.model_dump()) == set(results[1].answer.model_dump())


def test_main_returns_model_configuration_error(tmp_path: Path, monkeypatch):
    pdf = make_pdf(tmp_path)
    monkeypatch.setattr("app.cli.r0_demo.Settings", lambda: SimpleNamespace(OLLAMA_MODEL=""))
    exit_code = main(
        [
            "--pdf",
            str(pdf),
            "--question",
            "Question",
            "--output",
            str(tmp_path / "result.json"),
        ]
    )
    assert exit_code == 2
