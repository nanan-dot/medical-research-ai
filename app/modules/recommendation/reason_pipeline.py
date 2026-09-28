"""Versioned, deterministic facts and guarded wording for recommendation reasons."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field

FACT_SCHEMA_VERSION: Literal["recommendation-reason-facts-v1"] = "recommendation-reason-facts-v1"
OUTPUT_SCHEMA_VERSION: Literal["recommendation-reason-output-v1"] = "recommendation-reason-output-v1"
FORBIDDEN_CLAIM_TYPES = ["efficacy", "safety", "causality", "significance", "clinical_advice"]
UNSUPPORTED_WORDING = re.compile(r"证明|证实|显著改善|显著降低|应当采用|必然|因果|疗效|安全性")
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


class FactAtom(BaseModel):
    fact_id: str
    dimension: str
    label: str
    status: Literal["matched", "partial", "unavailable"]
    term: str | None = None
    display_text: str
    source_field: str
    verification_status: Literal["verified", "unverified", "unavailable"]


class LimitationFact(BaseModel):
    fact_id: str
    code: str
    message: str
    required_disclosure: bool = True


class ReasonSections(BaseModel):
    headline: str
    relevance: str
    incremental_value: str
    evidence_note: str
    limitation: str


class RecommendationReasonFactPacket(BaseModel):
    schema_version: Literal["recommendation-reason-facts-v1"] = FACT_SCHEMA_VERSION
    language: Literal["zh-CN"] = "zh-CN"
    generation_mode: Literal["intent_bound", "exploration"]
    recommendation_context: dict[str, object]
    article_evidence: dict[str, object]
    topic_matches: list[FactAtom]
    incremental_value: FactAtom
    evidence_quality: dict[str, object]
    limitations: list[LimitationFact]
    allowed_entities: list[str] = Field(default_factory=list)
    allowed_numbers: list[str] = Field(default_factory=list)
    forbidden_claim_types: list[str] = Field(default_factory=lambda: FORBIDDEN_CLAIM_TYPES.copy())
    base_reason: ReasonSections

    def fingerprint(self) -> str:
        return sha256(self.model_dump_json(exclude_none=True).encode()).hexdigest()


class ReasonSegment(BaseModel):
    text: str = Field(min_length=1, max_length=160)
    fact_ids: list[str] = Field(min_length=1)


class PolishedReasonOutput(BaseModel):
    schema_version: Literal["recommendation-reason-output-v1"] = OUTPUT_SCHEMA_VERSION
    headline: ReasonSegment
    relevance: ReasonSegment
    incremental_value: ReasonSegment
    limitation: ReasonSegment


def _fact_id(prefix: str, value: str) -> str:
    return f"{prefix}:{sha256(value.encode()).hexdigest()[:12]}"


def compile_fact_packet(
    *,
    source_result_id: int,
    intent_snapshot_id: int | None,
    exploration_query: str | None,
    recommendation_mode: str,
    year: int | None,
    publication_types: list[str],
    matches: list[dict[str, object]],
    overlap_status: str,
    limitations: list[dict[str, str]],
    incremental_detail: str | None = None,
) -> RecommendationReasonFactPacket:
    """Compile only already-computed recommendation evidence into display facts."""
    facts: list[FactAtom] = []
    for index, match in enumerate(matches):
        dimension = str(match.get("dimension", "topic"))
        status = str(match.get("status", "unavailable"))
        normalized: Literal["matched", "partial", "unavailable"] = "matched" if status == "matched" else "partial" if status == "partial" else "unavailable"
        raw_terms = match.get("matched_terms", [])
        terms = [str(value) for value in raw_terms] if isinstance(raw_terms, list) else []
        term = "、".join(terms) if terms else None
        facts.append(FactAtom(
            fact_id=_fact_id("topic", f"{index}|{dimension}|{term}|{normalized}"), dimension=dimension,
            label={"disease": "疾病", "intervention": "干预措施", "outcome": "结局", "population": "人群", "study_type": "研究类型", "evidence_fit": "研究设计"}.get(dimension, "研究主题"),
            status=normalized, term=term,
            display_text=str(match.get("display_text") or (f"{_field_label(str(match.get('field', 'metadata')))}中提及 {term}" if normalized == "matched" and term else "该维度尚无明确匹配证据")),
            source_field=str(match.get("field", "metadata")),
            verification_status="verified" if normalized == "matched" else "unavailable",
        ))
    if not facts:
        facts.append(FactAtom(fact_id=_fact_id("topic", "unavailable"), dimension="topic", label="研究主题", status="unavailable", display_text="可用主题信息不足", source_field="metadata", verification_status="unavailable"))
    incremental = FactAtom(
        fact_id=_fact_id("incremental", overlap_status), dimension="incremental_value", label="集合增量",
        status="matched" if overlap_status == "novel" else "partial", term=None,
        display_text=(incremental_detail or "当前集合之外的新增候选；尚未确认其提供新的研究结论") if overlap_status == "novel" else "该文献已在当前集合中出现",
        source_field="recommendation_overlap", verification_status="verified",
    )
    limit_facts = [LimitationFact(fact_id=_fact_id("limitation", f"{item['code']}|{item['message']}"), code=item["code"], message=item["message"]) for item in limitations]
    if not limit_facts:
        limit_facts = [LimitationFact(fact_id=_fact_id("limitation", "review"), code="evidence_review_needed", message="推荐理由基于可用元数据，仍需结合全文核验。")]
    matched = [fact for fact in facts if fact.status == "matched"]
    designs = [fact for fact in matched if fact.dimension == "study_type"]
    relevance = "；".join(fact.display_text for fact in matched) if matched else "尚无可核验的主题匹配证据，不能据此判断推荐价值。"
    design = "、".join(publication_types[:2]) if publication_types else "研究设计信息暂缺"
    base = ReasonSections(
        headline="；".join(fact.display_text for fact in designs) if designs else ("涉及 " + "、".join(dict.fromkeys(fact.term for fact in matched if fact.term))) if matched else "主题匹配依据不足",
        relevance=relevance,
        incremental_value=incremental.display_text,
        evidence_note=f"可识别的研究类型/证据特点：{design}。",
        limitation="；".join(item.message for item in limit_facts),
    )
    entities = sorted(
        {
            term
            for fact in facts
            if fact.verification_status == "verified" and fact.term
            for term in fact.term.split("、")
        }
    )
    return RecommendationReasonFactPacket(
        generation_mode="intent_bound" if intent_snapshot_id else "exploration",
        recommendation_context={"source_result_id": source_result_id, "intent_snapshot_id": intent_snapshot_id, "exploration_query": exploration_query, "recommendation_mode": recommendation_mode, "compiler_version": "2"},
        article_evidence={"metadata_status": "available", "publication_year": year, "study_design": publication_types[0] if publication_types else None, "study_design_verification": "verified" if publication_types else "unavailable", "fact_ids": [fact.fact_id for fact in facts if fact.dimension in {"study_type", "evidence_fit"}]},
        topic_matches=facts, incremental_value=incremental,
        evidence_quality={"level": "available_metadata", "reason_priority": ["topic_match", "study_design"]},
        limitations=limit_facts, allowed_entities=entities,
        allowed_numbers=[str(year)] if year else [], base_reason=base,
    )


def _field_label(field: str) -> str:
    labels = {"pubmed_title": "题名", "title": "题名", "pubmed_abstract_results": "摘要", "abstract": "摘要", "pubmed_mesh": "MeSH主题词", "pubmed_publication_types": "文献类型", "pubmed_publication_type": "文献类型"}
    return "、".join(labels.get(value, "元数据") for value in field.split(","))


@dataclass(frozen=True)
class PolishValidation:
    accepted: bool
    error_code: str | None = None


def validate_polished_reason(packet: RecommendationReasonFactPacket, raw: str) -> tuple[PolishedReasonOutput | None, PolishValidation]:
    """Reject whole model output unless every visible claim is bound to packet facts."""
    try:
        output = PolishedReasonOutput.model_validate_json(raw)
    except ValueError:
        return None, PolishValidation(False, "narration_invalid_json")
    fact_ids = {packet.incremental_value.fact_id, *(fact.fact_id for fact in packet.topic_matches), *(fact.fact_id for fact in packet.limitations)}
    sections = [output.headline, output.relevance, output.incremental_value, output.limitation]
    if any(not set(section.fact_ids) <= fact_ids for section in sections):
        return None, PolishValidation(False, "narration_unknown_fact_id")
    required_limitations = [fact for fact in packet.limitations if fact.required_disclosure]
    if not {fact.fact_id for fact in required_limitations} <= set(output.limitation.fact_ids):
        return None, PolishValidation(False, "narration_required_disclosure_missing")
    if any(fact.message not in output.limitation.text for fact in required_limitations):
        return None, PolishValidation(False, "narration_required_disclosure_missing")
    topic_by_id = {fact.fact_id: fact for fact in packet.topic_matches}
    for section in (output.headline, output.relevance):
        for fact_id in section.fact_ids:
            fact = topic_by_id.get(fact_id)
            if fact and fact.term and fact.term not in section.text:
                return None, PolishValidation(False, "narration_fact_text_mismatch")
    if (
        packet.incremental_value.fact_id in output.incremental_value.fact_ids
        and packet.incremental_value.display_text not in output.incremental_value.text
    ):
        return None, PolishValidation(False, "narration_fact_text_mismatch")
    rendered = " ".join(section.text for section in sections)
    if UNSUPPORTED_WORDING.search(rendered):
        return None, PolishValidation(False, "narration_medical_boundary")
    numbers = set(NUMBER_PATTERN.findall(rendered))
    if not numbers <= set(packet.allowed_numbers):
        return None, PolishValidation(False, "narration_new_number")
    if any(entity not in " ".join(packet.allowed_entities) for entity in re.findall(r"[A-Za-z][A-Za-z-]{2,}", rendered)):
        return None, PolishValidation(False, "narration_new_entity")
    if _contains_unapproved_chinese_claim(packet, rendered):
        return None, PolishValidation(False, "narration_new_entity")
    if len({section.text for section in sections}) != len(sections):
        return None, PolishValidation(False, "narration_repetitive")
    return output, PolishValidation(True)


def _contains_unapproved_chinese_claim(
    packet: RecommendationReasonFactPacket, rendered: str
) -> bool:
    """Reject Chinese clinical nouns/relations outside controlled fact wording."""
    remainder = rendered
    for text in (
        packet.base_reason.headline,
        packet.base_reason.relevance,
        packet.base_reason.incremental_value,
        packet.base_reason.evidence_note,
        packet.base_reason.limitation,
        *(fact.display_text for fact in packet.topic_matches),
        packet.incremental_value.display_text,
        *(fact.message for fact in packet.limitations),
        "与当前主题相关的候选",
        "相关候选",
        "与当前主题匹配",
        "当前主题",
        "推荐候选",
        "研究信息",
        "当前集合",
        "需要进一步核验",
    ):
        remainder = remainder.replace(text, "")
    for entity in packet.allowed_entities:
        remainder = remainder.replace(entity, "")
    return bool(re.search(r"[\u4e00-\u9fff]{2,}", remainder))


def narration_prompt(packet: RecommendationReasonFactPacket) -> str:
    """Return the minimal model input; identity metadata and source text are excluded."""
    payload = packet.model_dump(exclude={"recommendation_context", "article_evidence"})
    return "只能依据事实包和基础理由改写。不得新增疾病、药物、研究设计、数字或医学结论；不得输出PMID、DOI、作者、期刊、题名；必须保留限制；只返回指定JSON。\n" + json.dumps(payload, ensure_ascii=False)
