"""授权自制 PDF 与签名协议夹具；破坏测试显式修改签名后的流。"""

import hashlib
from pathlib import Path

from reportlab.pdfgen import canvas

from app.modules.document_anchor.contract import PageRecord, page_hash
from app.modules.document_anchor.fingerprint import document_content_hash
from tests.modules.document.conftest import create_document as create_base_document


async def create_document(session, root: Path, name: str = "paper.pdf"):
    document, path = await create_base_document(session, root, name=name)
    pdf = canvas.Canvas(str(path), invariant=1)
    pdf.drawString(72, 720, "Dose 5 mg")
    pdf.save()
    document.file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    document.file_size = path.stat().st_size
    await session.flush()
    return document, path


def seal(header: dict, pages: list[dict], trailer: dict) -> list[dict]:
    hashes = []
    for page in pages:
        page.setdefault("has_raster_image", False)
        page["page_content_hash"] = "0" * 64
        page["page_content_hash"] = page_hash(PageRecord.model_validate(page))
        hashes.append(page["page_content_hash"])
    trailer["document_content_hash"] = document_content_hash(hashes)
    return [header, *pages, trailer]
