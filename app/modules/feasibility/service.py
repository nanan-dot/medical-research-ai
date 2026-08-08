"""基于规则和用户自评保存可行性评分。"""
import json
from app.common.exceptions import ConflictError, NotFoundError
from app.modules.feasibility.model import FeasibilityScore
from app.modules.feasibility.repository import FeasibilityRepository
from app.modules.feasibility.schema import DimensionScore, FeasibilityRead, FeasibilityRequest, USER_DIMENSIONS
from app.modules.feasibility.scoring import DEFAULT_WEIGHTS, calculate_score, ranking_changed

class FeasibilityService:
    def __init__(self, session) -> None: self._repository = FeasibilityRepository(session)
    async def score(self, direction_id: int, payload: FeasibilityRequest) -> FeasibilityRead:
        direction = await self._repository.get_direction(direction_id)
        if direction is None: raise NotFoundError(f"Research direction not found: {direction_id}")
        weights = {**DEFAULT_WEIGHTS, **(payload.weights or {})}
        if any(value < 0 for value in weights.values()) or not any(weights.values()): raise ConflictError("Weights must include a positive value")
        assessments = {item.dimension: item for item in payload.user_assessments}
        dimensions = self._dimensions(direction, weights, assessments)
        total, confidence, missing = calculate_score(dimensions)
        if len(missing) == len(USER_DIMENSIONS): raise ConflictError("All user-assessment dimensions are unknown")
        versions = await self._repository.list_versions(direction_id)
        entity = await self._repository.create(FeasibilityScore(direction_id=direction_id, version=len(versions)+1, dimensions_json=json.dumps([item.model_dump() for item in dimensions], ensure_ascii=False), weights_json=json.dumps(weights), total_score=total, confidence=confidence, missing_inputs_json=json.dumps(missing), ranking_sensitive=ranking_changed(versions[-1].total_score if versions else None, total)))
        return self._read(entity)
    async def versions(self, direction_id: int) -> list[FeasibilityRead]: return [self._read(item) for item in await self._repository.list_versions(direction_id)]
    @staticmethod
    def _dimensions(direction, weights, assessments):
        system = {"literature_base": (min(100, len(json.loads(direction.evidence_json))*25), "证据矩阵中已绑定来源的文献依据。"), "novelty_uncertainty": (50, "新颖性不确定性仅用于比较，不代表发表概率。"), "technical_feasibility": (60 if direction.methods else 40, "依据候选详情是否已明确方法。"), "analysis_difficulty": (60, "分析难度需结合方法与导师意见复核。"), "advisor_alignment": (50, "未从条件中推断导师承诺，使用中性规则分。")}
        rows=[]
        for name, weight in weights.items():
            if name in system:
                score,basis=system[name]; rows.append(DimensionScore(dimension=name,score=score,weight=weight,basis=basis,score_source="system"))
            else:
                assessment=assessments.get(name); rows.append(DimensionScore(dimension=name,score=assessment.score if assessment else None,weight=weight,basis=assessment.basis if assessment and assessment.basis else "未填写，未参与加权。",score_source="user" if assessment and assessment.score is not None else "unknown"))
        return rows
    @staticmethod
    def _read(entity): return FeasibilityRead(id=entity.id,direction_id=entity.direction_id,version=entity.version,dimensions=[DimensionScore.model_validate(item) for item in json.loads(entity.dimensions_json)],weights=json.loads(entity.weights_json),total_score=entity.total_score,confidence=entity.confidence,missing_inputs=json.loads(entity.missing_inputs_json),ranking_sensitive=entity.ranking_sensitive,created_at=entity.created_at)
