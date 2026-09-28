"""Conservative condition parsing and metadata-bound assessment."""

import re
from datetime import UTC, date, datetime

from app.modules.document.parsers.schemas import ParsedDocument
from app.modules.document_navigation.schema import (
    ConditionMatchStatus,
    NavigationCondition,
    NavigationConditionMatch,
    VerificationStatus,
)

_RCT_QUERY = re.compile(
    r"随机[对照化]试验|随机对照|randomi[sz]ed controlled trial|\bRCT\b",
    re.IGNORECASE,
)
_RCT_METADATA = re.compile(
    r"随机[对照化]试验|随机对照|randomi[sz]ed controlled trial|\bRCT\b",
    re.IGNORECASE,
)
_NEGATED_RCT_METADATA = re.compile(
    r"non[- ]?random|not (?:an? )?(?:rct|randomi[sz]ed)|不是\s*RCT|非随机|未随机",
    re.IGNORECASE,
)
_PUBLICATION_YEAR_FIELDS = ("publication_year", "published_year", "year")
_STUDY_DESIGN_FIELDS = ("study_design", "publication_type", "publication_types")


def requested_navigation_conditions(
    query: str, *, today: date | None = None
) -> list[NavigationCondition]:
    """Parse only the small, explicit constraint vocabulary supported by navigation."""

    current_year = (today or datetime.now(UTC).date()).year
    conditions: list[NavigationCondition] = []
    if "近三年" in query:
        first_year = current_year - 2
        conditions.append(
            NavigationCondition(
                condition_id="publication_period_recent_3y",
                label="近三年",
                field="publication_year",
                expected_value=f"{first_year}-{current_year}",
                status=VerificationStatus.UNVERIFIED,
                reason="仅由结构化出版年份元数据评估；正文年份不作为出版年份事实。",
            )
        )
    if _RCT_QUERY.search(query):
        conditions.append(
            NavigationCondition(
                condition_id="study_design_rct",
                label="随机对照试验",
                field="study_design",
                expected_value="randomized controlled trial",
                status=VerificationStatus.UNVERIFIED,
                reason="仅由结构化研究类型元数据评估；正文命中只记录为提及。",
            )
        )
    return conditions


def match_navigation_conditions(
    requested: list[NavigationCondition], parsed: ParsedDocument, text: str
) -> list[NavigationConditionMatch]:
    """Assess constraints without promoting unstructured text to metadata facts."""

    matches: list[NavigationConditionMatch] = []
    for condition in requested:
        if condition.condition_id == "publication_period_recent_3y":
            matches.append(_match_publication_period(condition, parsed.yaml_metadata))
        elif condition.condition_id == "study_design_rct":
            matches.append(_match_study_design(condition, parsed.yaml_metadata, text))
        else:
            matches.append(_not_assessed(condition, "当前条件类型尚无可信评估器。"))
    return matches


def _match_publication_period(
    condition: NavigationCondition, metadata: dict[str, object]
) -> NavigationConditionMatch:
    value, field = _first_metadata_value(metadata, _PUBLICATION_YEAR_FIELDS)
    year = _coerce_year(value)
    if year is None or field is None or condition.expected_value is None:
        return _not_assessed(condition, "缺少可信的结构化出版年份元数据。")
    first_year, last_year = (int(part) for part in condition.expected_value.split("-", 1))
    is_match = first_year <= year <= last_year
    return NavigationConditionMatch(
        condition_id=condition.condition_id,
        label=condition.label,
        status=(
            ConditionMatchStatus.METADATA_MATCH
            if is_match
            else ConditionMatchStatus.METADATA_MISMATCH
        ),
        basis="metadata",
        reason=("出版年份位于请求范围内。" if is_match else "出版年份不在请求范围内。"),
        source_field=field,
        evidence_span=str(year),
    )


def _match_study_design(
    condition: NavigationCondition, metadata: dict[str, object], text: str
) -> NavigationConditionMatch:
    value, field = _first_metadata_value(metadata, _STUDY_DESIGN_FIELDS)
    if field is not None:
        display_value = _display_metadata(value)
        is_match = _metadata_declares_rct(value)
        return NavigationConditionMatch(
            condition_id=condition.condition_id,
            label=condition.label,
            status=(
                ConditionMatchStatus.METADATA_MATCH
                if is_match
                else ConditionMatchStatus.METADATA_MISMATCH
            ),
            basis="metadata",
            reason=("研究类型元数据明确为随机对照试验。" if is_match else "研究类型元数据未标记为随机对照试验。"),
            source_field=field,
            evidence_span=display_value[:160],
        )
    mention = _RCT_QUERY.search(text)
    if mention:
        return NavigationConditionMatch(
            condition_id=condition.condition_id,
            label=condition.label,
            status=ConditionMatchStatus.TEXT_MENTION,
            basis="text",
            reason="正文仅提及该研究类型，不能据此确认文献设计。",
            evidence_span=mention.group(0),
        )
    return _not_assessed(condition, "缺少可信的结构化研究类型元数据。")


def _not_assessed(
    condition: NavigationCondition, reason: str
) -> NavigationConditionMatch:
    return NavigationConditionMatch(
        condition_id=condition.condition_id,
        label=condition.label,
        status=ConditionMatchStatus.NOT_ASSESSED,
        basis="none",
        reason=reason,
    )


def _first_metadata_value(
    metadata: dict[str, object], fields: tuple[str, ...]
) -> tuple[object | None, str | None]:
    normalized = {str(key).casefold(): value for key, value in metadata.items()}
    for field in fields:
        if field in normalized and normalized[field] not in (None, "", []):
            return normalized[field], field
    return None, None


def _coerce_year(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 1900 <= value <= 2100:
        return value
    if isinstance(value, str) and re.fullmatch(r"(?:19|20)\d{2}", value.strip()):
        return int(value)
    return None


def _display_metadata(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


def _metadata_declares_rct(value: object) -> bool:
    values = value if isinstance(value, list) else [value]
    return any(
        _RCT_METADATA.search(str(item))
        and not _NEGATED_RCT_METADATA.search(str(item))
        for item in values
    )
