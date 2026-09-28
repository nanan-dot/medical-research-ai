"""Create an isolated synthetic two-page PDF + real A0/A1 database for browser QA."""

import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base
from app.modules.document.model import Document
from app.modules.document.service import DocumentService
from app.modules.document_anchor.extractor_runner import PdfTextItemExtractor
from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.document_anchor.publisher import publish
from app.modules.document_anchor.toolchain import (
    EXTRACTOR_VERSION,
    NORMALIZATION_VERSION,
    OPTIONS_HASH,
    PDFJS_VERSION,
)
from app.modules.document_layout.service import DocumentLayoutService
from app.modules.knowledge_source.model import KnowledgeSource


async def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="a2-browser-", dir="work")).resolve()
    source_dir = root / "source"
    source_dir.mkdir()
    pdf_path = source_dir / "synthetic-selection.pdf"
    pdf = canvas.Canvas(str(pdf_path), invariant=1)
    for number in (1, 2):
        pdf.setFont("Helvetica", 12)
        pdf.drawString(72, 690, f"Synthetic page {number}. Dose 5 mg.")
        pdf.drawString(72, 620, "Repeated sentence for anchor positioning.")
        pdf.showPage()
    pdf.save()
    file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    database_url = f"sqlite+aiosqlite:///{(root / 'app.db').as_posix()}"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        source = KnowledgeSource(name="A2 synthetic browser validation", source_type="local_folder",
            root_path=str(source_dir), normalized_root_path=str(source_dir).casefold(), enabled=True, sync_status="idle")
        session.add(source)
        await session.flush()
        stat = pdf_path.stat()
        document = Document(knowledge_source_id=source.id, file_path=pdf_path.name,
            normalized_file_path=pdf_path.name, file_hash=file_hash, file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime, UTC), modified_time_ns=stat.st_mtime_ns,
            scan_state="pending", parse_status="pending", index_status="outdated")
        session.add(document)
        await session.flush()
        await DocumentService(session).parse(document.id)
        revision = DocumentAnchorRevision(document_id=document.id, file_hash=file_hash,
            request_fingerprint="a" * 64, extractor_version=EXTRACTOR_VERSION,
            pdfjs_version=PDFJS_VERSION, normalization_version=NORMALIZATION_VERSION,
            options_hash=OPTIONS_HASH, state="pending")
        session.add(revision)
        await session.flush()
        stream = await PdfTextItemExtractor().extract(pdf_path, file_hash, "a2-browser")
        try:
            await publish(session, revision, stream)
        finally:
            stream.close()
        await session.commit()
        layout = await DocumentLayoutService(session).request(revision.id)
        await DocumentLayoutService(session).execute(layout.id)
        await session.commit()
        print(json.dumps({"database_url": database_url, "document_id": document.id,
            "directory": str(root), "file_hash": file_hash, "anchor_revision_id": revision.id,
            "segmentation_revision_id": layout.id}))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
