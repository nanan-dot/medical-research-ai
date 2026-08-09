from fastapi.testclient import TestClient

from app.main import app
from app.modules.recommendation.router import get_recommendation_service
from app.modules.recommendation.schema import RecommendationResponse


class FakeRecommendationService:
    async def recommend(
        self, query: str, *, candidate_count: int = 5
    ) -> RecommendationResponse:
        return RecommendationResponse(
            query=query,
            status="completed_with_warnings",
            items=[],
            warnings=["未找到可验证文献"],
        )


def test_recommendation_api_returns_explicit_empty_result_state() -> None:
    async def override_service() -> FakeRecommendationService:
        return FakeRecommendationService()

    app.dependency_overrides[get_recommendation_service] = override_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/recommendations",
                json={"query": "肺癌免疫治疗", "candidate_count": 3},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "completed_with_warnings"
    assert response.json()["items"] == []
    assert response.json()["warnings"] == ["未找到可验证文献"]
