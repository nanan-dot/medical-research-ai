"""Document parser boundary."""

from app.modules.document.parsers.factory import create_parser
from app.modules.document.parsers.schemas import ParsedDocument, ParsedPage, ParsedSection

__all__ = ["ParsedDocument", "ParsedPage", "ParsedSection", "create_parser"]
