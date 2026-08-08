from app.modules.recommendation.router import router


def test_recommendation_router_exposes_post_endpoint() -> None:
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}

    assert ("/recommendations", ("POST",)) in routes
