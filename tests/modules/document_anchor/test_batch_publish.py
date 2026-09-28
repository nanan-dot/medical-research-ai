"""数据库写入批次上限与较大页面的集成验收。"""

from sqlalchemy import event, func, select

from app.modules.document_anchor.contract import validate_records
from app.modules.document_anchor.model import DocumentSourceTextItem
from app.modules.document_anchor.schema import AnchorRevisionRequest
from app.modules.document_anchor.service import DocumentAnchorService
from tests.modules.document_anchor.support import create_document, seal
from tests.modules.document_anchor.test_acceptance import _header, _page, _trailer


async def test_large_page_uses_bounded_bulk_inserts(session, tmp_path):
    document, _ = await create_document(session, tmp_path / "source")
    service = DocumentAnchorService(session)
    revision = await service.request(
        document.id, AnchorRevisionRequest(expected_file_hash=document.file_hash)
    )

    class Large:
        async def extract(self, path, sha, request_id):
            header, page, trailer = _header(), _page(), _trailer()
            header.update(file_sha256=sha, request_id=request_id)
            trailer.update(request_id=request_id, items_emitted=1201)
            template = page["items"][0]
            page["items"] = [
                {
                    **template,
                    "item_index": i,
                    "source_array_index": i,
                    "transform": [1, 0, 0, 1, i % 500, 10 + i // 500],
                }
                for i in range(1201)
            ]
            return validate_records(seal(header, [page], trailer))

    batches = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO document_source_text_items"):
            batches.append(len(parameters) if executemany else 1)

    event.listen(session.bind.sync_engine, "before_cursor_execute", observe)
    try:
        await service.execute(revision.id, Large())
        assert batches == [500, 500, 201]
        assert (
            await session.scalar(
                select(func.count()).select_from(DocumentSourceTextItem)
            )
            == 1201
        )
    finally:
        event.remove(session.bind.sync_engine, "before_cursor_execute", observe)
