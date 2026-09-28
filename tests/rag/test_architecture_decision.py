from app.core.config import Settings
from app.rag.answer_service import Generator


def test_default_architecture_keeps_paperqa_and_candidate_chain_disabled() -> None:
    settings = Settings()
    assert settings.GROUNDED_RAG_MODE == "paperqa"
    assert settings.GROUNDED_RAG_ENABLED is False
    assert settings.RERANK_ENABLED is False


def test_generator_contract_is_vendor_neutral() -> None:
    assert set(Generator.__annotations__) == {"model_version"}
