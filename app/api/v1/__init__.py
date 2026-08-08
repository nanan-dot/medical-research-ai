"""API v1 路由聚合"""

from fastapi import APIRouter

from app.modules.health.router import router as health_router
from app.modules.model_config.router import router as model_config_router
from app.modules.knowledge_source.router import router as knowledge_source_router
from app.modules.document.router import router as document_router
from app.modules.conversation.router import router as conversation_router
from app.modules.paper_analysis.router import router as paper_analysis_router
from app.modules.literature_search.router import (
    duplicate_group_router,
    router as literature_search_router,
)
from app.modules.research_direction.router import router as research_direction_router
from app.modules.writing.router import router as writing_router
from app.modules.feedback.router import router as feedback_router
from app.modules.evaluation.router import router as evaluation_router
from app.modules.export.router import router as export_router
from app.modules.citation_check.router import router as citation_check_router
from app.modules.library_item.router import router as library_item_router, save_router as library_save_router
from app.modules.comparison.router import router as comparison_router
from app.modules.evidence_matrix.router import router as evidence_matrix_router
from app.modules.research_conditions.router import router as research_conditions_router
from app.modules.topic_structuring.router import router as topic_structuring_router
from app.modules.evidence_analysis.router import router as evidence_analysis_router

api_router = APIRouter()
api_router.include_router(library_save_router)
api_router.include_router(library_item_router)
api_router.include_router(comparison_router, tags=["comparison"])
api_router.include_router(evidence_matrix_router, tags=["证据矩阵"])
api_router.include_router(research_conditions_router)
api_router.include_router(topic_structuring_router)
api_router.include_router(evidence_analysis_router)
api_router.include_router(export_router, tags=["导出"])

api_router.include_router(health_router, tags=["健康检查"])
api_router.include_router(model_config_router, tags=["模型配置"])
api_router.include_router(knowledge_source_router, tags=["知识源"])
api_router.include_router(document_router, tags=["文档"])
api_router.include_router(conversation_router, tags=["会话"])
api_router.include_router(paper_analysis_router, tags=["论文分析"])
api_router.include_router(literature_search_router, tags=["文献检索"])
api_router.include_router(duplicate_group_router, tags=["文献去重"])
api_router.include_router(research_direction_router, tags=["研究方向"])
api_router.include_router(writing_router, tags=["写作"])
api_router.include_router(feedback_router, tags=["反馈"])
api_router.include_router(evaluation_router, tags=["评测"])
api_router.include_router(citation_check_router, tags=["引用核验"])
