from app.modules.writing_project.router import router


def test_writing_project_router_exposes_required_mutating_endpoints() -> None:
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}
    assert ("/writing-projects", ("POST",)) in routes
    assert ("/writing-projects", ("GET",)) in routes
    assert ("/writing-projects/{project_id}", ("PATCH",)) in routes
    assert ("/writing-projects/{project_id}", ("DELETE",)) in routes
    assert ("/writing-projects/{project_id}/versions", ("POST",)) in routes
    assert ("/writing-projects/{project_id}/versions", ("GET",)) in routes
    assert (
        "/writing-projects/{project_id}/versions/{version}/restore",
        ("POST",),
    ) in routes
