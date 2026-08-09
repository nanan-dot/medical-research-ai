"""研究条件 known 语义和版本快照测试。"""

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.modules.research_conditions.schema import (
    ResearchConditionsCreate,
    ResearchConditionsPatch,
)
from app.modules.research_conditions.service import ResearchConditionsService
from app.modules.research_conditions.validation import exclude_unknown_fields


def _minimal_payload() -> dict[str, object]:
    return {
        "specialty": {"value": "oncology", "known": True, "source": "user"},
        "feasible_research_types": {
            "value": ["clinical", "bioinformatics"],
            "known": True,
            "source": "user",
        },
        "sample_source": {"value": None, "known": False, "source": "unknown"},
        "uncertain_notes": "sample access is uncertain",
    }


def test_illegal_feasible_research_type_is_rejected() -> None:
    payload = _minimal_payload()
    payload["feasible_research_types"] = {
        "value": ["clinical", "invalid"],
        "known": True,
        "source": "user",
    }
    with pytest.raises(
        ValidationError, match="allowed values: clinical, animal, cell, bioinformatics"
    ):
        ResearchConditionsCreate.model_validate(payload)


def test_unknown_field_is_preserved_and_excluded_from_model_input() -> None:
    conditions = ResearchConditionsCreate.model_validate(_minimal_payload())
    assert conditions.sample_source is not None
    assert conditions.sample_source.known is False
    model_input = exclude_unknown_fields(
        conditions.model_dump(exclude={"uncertain_notes"})
    )
    assert "sample_source" not in model_input
    assert model_input["specialty"] == "oncology"


def test_empty_conditions_are_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one minimal input field"):
        ResearchConditionsCreate.model_validate(
            {"specialty": {"value": None, "known": False, "source": "unknown"}}
        )


@pytest.mark.asyncio
async def test_patch_increments_version_and_keeps_uncertain_notes_separate() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        service = ResearchConditionsService(session)
        created = await service.create(
            ResearchConditionsCreate.model_validate(_minimal_payload())
        )
        patched = await service.patch(
            created.id,
            ResearchConditionsPatch.model_validate(
                {"budget": {"value": "limited", "known": True, "source": "user"}}
            ),
        )
        assert patched.conditions_version == 2
        assert patched.uncertain_notes == "sample access is uncertain"
        assert patched.budget is not None
        assert patched.budget.value == "limited"
    await engine.dispose()
