"""无 I/O 的评分计算，禁止模型主观打分。"""
from app.modules.feasibility.schema import Confidence, DimensionName, DimensionScore, USER_DIMENSIONS

DEFAULT_WEIGHTS: dict[DimensionName, float] = {"literature_base": 1, "novelty_uncertainty": 1, "technical_feasibility": 1, "sample_availability": 1, "data_availability": 1, "timeline": 1, "budget": 1, "ethics": 1, "analysis_difficulty": 1, "advisor_alignment": 1}

def calculate_score(dimensions: list[DimensionScore]) -> tuple[float, Confidence, list[DimensionName]]:
    """按有效权重求相对分，并将用户未知信息反映为置信度而非猜测分数。"""
    missing = [item.dimension for item in dimensions if item.dimension in USER_DIMENSIONS and item.score is None]
    weighted = [item for item in dimensions if item.score is not None and item.weight > 0]
    if not weighted: raise ValueError("No scored dimensions with positive weights")
    denominator = sum(item.weight for item in weighted)
    total = round(sum(item.weight * item.score for item in weighted if item.score is not None) / denominator, 1)
    confidence: Confidence = "low" if len(missing) > 2 else "medium" if missing else "high"
    return total, confidence, missing

def ranking_changed(previous_score: float | None, current_score: float) -> bool:
    """单方向版本以总分变化提示权重敏感；跨候选排名由前端比较版本。"""
    return previous_score is not None and previous_score != current_score
