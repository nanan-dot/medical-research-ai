"""来源策略与统一轮次契约，测试可观察行为而非内部实现。"""

import pytest
from pydantic import ValidationError

from app.modules.unified_conversation.query_router import QueryRouter
from app.modules.unified_conversation.schema import (
    ConversationMode,
    UnifiedMessageCreate,
)


def test_general_mode_cannot_silently_ignore_explicit_paper_requirement():
    result = QueryRouter().route(
        "仅依据文献解释这篇论文", ConversationMode.GENERAL, has_documents=True
    )
    assert result.requires_scope
    assert result.reason_code == "source_conflict"


def test_concept_sample_size_is_general_without_document_scope():
    result = QueryRouter().route(
        "什么是样本量", ConversationMode.AUTO, has_documents=False
    )
    assert not result.requires_scope
    assert result.reason_code == "general_explanation"


def test_blank_message_is_rejected():
    with pytest.raises(ValidationError):
        UnifiedMessageCreate(message="   ")


def test_unknown_request_fields_are_rejected():
    with pytest.raises(ValidationError):
        UnifiedMessageCreate(message="你好", execute_tool="shell")
