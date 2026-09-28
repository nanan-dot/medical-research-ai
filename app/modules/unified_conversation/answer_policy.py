"""基于实际来源保留局部证据，不把未知片段变成论文结论。"""

from app.integrations.paperqa2 import PaperQAAnswer
from app.modules.conversation.no_answer import evaluate_answer
from app.modules.unified_conversation.schema import (
    UnifiedAnswerSection,
    UnifiedCitationRead,
)


def paper_section(document_id: int, answer: PaperQAAnswer) -> UnifiedAnswerSection:
    decision = evaluate_answer([answer])
    citations = [
        UnifiedCitationRead(
            document_id=document_id,
            page=source.page_start,
            section=source.title,
            evidence_text=source.excerpt,
            citation_text=source.citation,
        )
        for source in answer.sources
    ]
    if decision.status == "answered":
        return UnifiedAnswerSection(
            source_type="paper_grounded", content=answer.answer, citations=citations
        )
    if (
        "no_sources" not in decision.reason_codes
        and "low_relevance" not in decision.reason_codes
    ):
        snippets = [item.evidence_text for item in citations if item.evidence_text]
        if snippets:
            return UnifiedAnswerSection(
                source_type="paper_grounded",
                answer_status="partial",
                content="本次检索提供了以下证据片段，但不足以确认问题中的全部结论，请结合原文核对：\n\n"
                + "\n\n".join(snippets),
                citations=citations,
            )
    return UnifiedAnswerSection(
        source_type="paper_grounded",
        answer_status="insufficient_evidence",
        content=f"在本次检索的文献 {document_id} 中未找到足够证据回答此问题。",
        citations=[],
    )
