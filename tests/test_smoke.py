"""核心模块冒烟测试"""

import pytest


def test_config_loads():
    from app.core.config import settings

    assert settings.APP_NAME == "医学科研智能助手平台"
    assert settings.APP_VERSION == "0.1.0"


def test_database_base():
    from app.core.database import Base

    assert Base is not None


@pytest.mark.parametrize(
    "module_name",
    [
        "health",
        "model_config",
        "knowledge_source",
        "document",
        "conversation",
        "paper_analysis",
        "literature_search",
        "research_direction",
        "writing",
        "feedback",
        "evaluation",
    ],
)
def test_module_imports(module_name):
    """验证每个模块的 model 可导入"""
    mod = __import__(f"app.modules.{module_name}.model", fromlist=["*"])
    # 每个模块都应有对应的 Model 类
    assert mod is not None


def test_api_router_has_all_modules():
    from app.api.v1 import api_router

    assert len(api_router.routes) >= 11, (
        f"expected >=11 routes, got {len(api_router.routes)}"
    )
