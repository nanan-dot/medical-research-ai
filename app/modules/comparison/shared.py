"""Shared evidence-backed comparison / matrix building blocks (R2-WP11/12).

FIELD_MAPPING 把比较字段映射到 paper_analysis structured_result 的字段名，
由 comparison 与 evidence_matrix 两个模块共用，保证"从单篇结构化分析取
证据"的规则只有一份实现。
"""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

# 缺失值的统一展示（review-paper：绝不编造缺失数据）。
MISSING_VALUE = "缺失"


class ComparisonField(StrEnum):
    STUDY_TYPE = "study_type"
    STUDY_POPULATION = "study_population"
    SAMPLE_SIZE = "sample_size"
    INTERVENTION = "intervention"
    COMPARATOR = "comparator"
    OUTCOME = "outcome"
    METHODS = "methods"
    STATISTICS = "statistics"
    RESULTS = "results"
    NOVELTY = "novelty"
    LIMITATIONS = "limitations"
    SOURCE = "source"


# 默认矩阵/比较字段集（证据矩阵预置字段用同一份）。
DEFAULT_FIELDS = tuple(ComparisonField)

# 比较字段 -> paper_analysis.structured_result 字段名。
FIELD_MAPPING = {
    ComparisonField.STUDY_TYPE: "study_type",
    ComparisonField.STUDY_POPULATION: "population",
    ComparisonField.SAMPLE_SIZE: "sample_size",
    ComparisonField.INTERVENTION: "intervention_or_exposure",
    ComparisonField.COMPARATOR: "comparator",
    ComparisonField.OUTCOME: "primary_outcome",
    ComparisonField.METHODS: "research_question",
    ComparisonField.STATISTICS: "statistical_methods",
    ComparisonField.RESULTS: "main_results",
    ComparisonField.NOVELTY: "innovations",
    ComparisonField.LIMITATIONS: "limitations",
}


class CellStatus(StrEnum):
    GENERATED = "generated"
    USER_EDITED = "user_edited"
    MISSING = "missing"


class SourceRef(BaseModel):
    pmid: str | None = Field(default=None, pattern=r"^\d{1,20}$")
    doi: str | None = Field(default=None, pattern=r"^10\.\d{4,9}/\S+$")
    locator: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def require_identifier(self) -> "SourceRef":
        if self.pmid is None and self.doi is None:
            raise ValueError("Source requires PMID or DOI")
        return self


class ComparisonCellGenerated(BaseModel):
    document_id: int
    field: ComparisonField
    generated_value: str | None = None
    sources: list[SourceRef] = Field(default_factory=list)
    cell_value: str = MISSING_VALUE
    status: CellStatus = CellStatus.MISSING

    @model_validator(mode="after")
    def enforce_evidence(self) -> "ComparisonCellGenerated":
        # 无来源的值不得标记为 generated（缺失显式标注）。
        if self.generated_value and self.sources:
            self.cell_value = self.generated_value
            self.status = CellStatus.GENERATED
        return self
