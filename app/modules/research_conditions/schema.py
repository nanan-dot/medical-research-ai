"""研究条件快照的请求与响应结构。"""

from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.research_conditions.validation import (
    validate_feasible_research_types,
    validate_field_state,
    validate_nonempty_minimal_input,
)

ConditionValue: TypeAlias = str | int | list[str] | None
ConditionSource = Literal["user", "unknown"]


class ConditionField(BaseModel):
    """单个条件的用户态；unknown 是显式信息，不是可由模型补全的缺失值。"""

    value: ConditionValue = None
    known: bool
    source: ConditionSource

    @model_validator(mode="after")
    def validate_state(self) -> "ConditionField":
        validate_field_state(known=self.known, source=self.source, value=self.value)
        return self


class FeasibleResearchTypesField(ConditionField):
    value: list[str] | None = None

    @model_validator(mode="after")
    def validate_types(self) -> "FeasibleResearchTypesField":
        if self.known and self.value is not None:
            validate_feasible_research_types(self.value)
        return self


class ResearchConditionsInput(BaseModel):
    """最小输入与高级条件；未提交字段保持未填写，显式未知必须用 known=false 表示。"""

    specialty: ConditionField | None = None
    advisor_direction: ConditionField | None = None
    interest_topic: ConditionField | None = None
    existing_papers: ConditionField | None = None
    feasible_research_types: FeasibleResearchTypesField | None = None
    sample_source: ConditionField | None = None
    sample_size: ConditionField | None = None
    technical_conditions: ConditionField | None = None
    equipment: ConditionField | None = None
    data_resources: ConditionField | None = None
    budget: ConditionField | None = None
    timeline: ConditionField | None = None
    ethics_conditions: ConditionField | None = None
    collaboration_resources: ConditionField | None = None
    prohibited_content: ConditionField | None = None
    uncertain_notes: str | None = Field(default=None, max_length=2000)


class ResearchConditionsCreate(ResearchConditionsInput):
    """创建一组研究条件，生成初始版本。"""

    @model_validator(mode="after")
    def validate_minimal_input(self) -> "ResearchConditionsCreate":
        validate_nonempty_minimal_input(self.model_dump(exclude={"uncertain_notes"}))
        return self


class ResearchConditionsPatch(ResearchConditionsInput):
    """只提交需修改字段；服务层合并为完整快照后再校验最小输入。"""


class ResearchConditionsRead(ResearchConditionsInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conditions_version: int
    created_at: datetime
    updated_at: datetime
