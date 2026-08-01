"""Stable PaperQA2 adapter surface."""

from app.integrations.paperqa2.client import PaperQA2Client
from app.integrations.paperqa2.factory import create_paperqa2_client
from app.integrations.paperqa2.schemas import (
    PaperDocument,
    PaperQAAnswer,
    PaperQAIndex,
    PaperSource,
)

__all__ = [
    "PaperDocument",
    "PaperQA2Client",
    "PaperQAAnswer",
    "PaperQAIndex",
    "PaperSource",
    "create_paperqa2_client",
]
