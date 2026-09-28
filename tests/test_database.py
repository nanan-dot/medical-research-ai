"""SQLAlchemy 模型注册与异步会话事务测试。"""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import database, models  # noqa: F401 - register all models
from app.core.database import Base

EXPECTED_TABLES = {
    "agent_artifacts",
    "agent_budget_reservations",
    "agent_events",
    "agent_external_executions",
    "agent_idempotency_records",
    "agent_outbox",
    "agent_role_qualifications",
    "agent_root_budgets",
    "agent_runs",
    "agent_steps",
    "agent_task_requests",
    "artifact_dependencies",
    "invalidation_records",
    "model_transfer_authorizations",
    "paper_research_center_preferences",
    "research_context_memberships",
    "role_decisions",
    "unified_chat_turns",
    "unified_knowledge_gaps",
    "user_confirmations",
    "conversations",
    "messages",
    "citations",
    "documents",
    "document_anchor_revisions",
    "document_assets",
    "document_annotations",
    "document_ocr_jobs",
    "document_ocr_pages",
    "document_source_pages",
    "document_source_text_items",
    "document_segmentation_revisions",
    "document_layout_blocks",
    "document_layout_sections",
    "document_layout_segments",
    "document_layout_fragments",
    "document_source_anchors",
    "document_anchor_fragments",
    "document_anchor_segments",
    "document_reading_notes",
    "document_selection_operations",
    "document_file_revisions",
    "document_anchor_relocations",
    "document_anchor_relocation_decisions",
    "asset_anchor_links",
    "legacy_anchor_backfill_runs",
    "legacy_anchor_backfill_items",
    "document_accesses",
    "evaluations",
    "exports",
    "feedbacks",
    "healths",
    "knowledge_sources",
    "journal_metric_import_batches",
    "knowledge_source_research_contexts",
    "literature_searchs",
    "literature_search_results",
    "literature_search_tasks",
    "literature_search_task_results",
    "literature_search_item_state",
    "literature_search_strategies",
    "literature_search_strategy_versions",
    "literature_search_executions",
    "literature_commercial_journal_metrics",
    "literature_score_generations",
    "literature_article_scores",
    "literature_research_intent_snapshots",
    "literature_duplicate_groups",
    "literature_duplicate_group_members",
    "literature_duplicate_resolutions",
    "literature_reading_orders",
    "reading_plans",
    "reading_plan_items",
    "reader_sessions",
    "reader_page_exposures",
    "reader_preferences",
    "reader_bookmarks",
    "reader_questions",
    "reader_idempotency_records",
    "research_material_candidates",
    "paper_reader_states",
    "recommendation_runs",
    "recommendation_candidates",
    "recommendation_decisions",
    "recommendation_narration_leases",
    "library_items",
    "fulltext_retrievals",
    "comparison_tasks",
    "comparison_cells",
    "evidence_matrices",
    "matrix_documents",
    "matrix_fields",
    "matrix_cells",
    "model_configs",
    "medical_translation_jobs",
    "paper_analysiss",
    "research_directions",
    "feasibility_scores",
    "feasibility_weight_profiles",
    "advisor_reviews",
    "direction_revisions",
    "presentations",
    "outlines",
    "writing_projects",
    "writing_generated_contents",
    "writing_user_materials",
    "writing_versions",
    "ai_usage_events",
    "ai_disclosure_drafts",
    "research_conditions",
    "research_conditions_versions",
    "research_contexts",
    "research_context_documents",
    "topic_structurings",
    "topic_structuring_versions",
    "translation_revisions",
    "translation_validation_reports",
    "translation_reviews",
    "translation_term_overrides",
    "task_records",
    "evaluation_runs",
    "evaluation_run_results",
    "literature_status_records",
    "search_strategy_drafts",
    "search_strategy_terms",
    "search_strategy_mesh_terms",
    "search_strategy_versions",
    "writings",
    "writing_evidence_references",
    "writing_ai_suggestions",
    "writing_reviews",
    "zotero_libraries",
    "zotero_collections",
    "note_activities",
    "note_ai_suggestions",
    "note_derivations",
    "note_drafts",
    "note_legacy_backfills",
    "note_research_links",
    "note_revisions",
    "note_save_operations",
    "note_source_links",
    "note_tag_links",
    "note_tags",
    "research_notes",
    "paper_activities",
    "paper_library_members",
    "paper_research_relations",
    "paper_tags",
    "paper_work_states",
}


def test_all_models_are_registered():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.asyncio
async def test_sqlite_file_is_created(tmp_path: Path):
    database_path = tmp_path / "app.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await engine.dispose()
    assert database_path.is_file()


@pytest.mark.asyncio
async def test_get_session_rolls_back_on_exception(tmp_path: Path, monkeypatch):
    database_path = tmp_path / "rollback.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with test_engine.begin() as connection:
        await connection.execute(text("CREATE TABLE rollback_probe (value INTEGER)"))

    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)
    session_dependency = database.get_session()
    session = await anext(session_dependency)
    await session.execute(text("INSERT INTO rollback_probe (value) VALUES (1)"))

    with pytest.raises(RuntimeError, match="force rollback"):
        await session_dependency.athrow(RuntimeError("force rollback"))

    async with session_factory() as verification_session:
        result = await verification_session.execute(
            text("SELECT COUNT(*) FROM rollback_probe")
        )
        assert result.scalar_one() == 0

    await test_engine.dispose()
