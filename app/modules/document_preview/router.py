"""文档原文预览与受控 PDF 流接口。"""

from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_preview.schema import DocumentPreviewRead
from app.modules.document_preview.service import DocumentPreviewService

router = APIRouter(tags=["document-preview"])

# 单块上限：客户端请求超大 Range 时按此切片，避免一次读入整个文件。
_CHUNK_LIMIT_BYTES = 1024 * 1024


@router.get("/documents/{document_id}/preview", response_model=DocumentPreviewRead)
async def get_document_preview(
    document_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentPreviewRead:
    return await DocumentPreviewService(session).get_preview(document_id)


@router.get("/documents/{document_id}/original")
async def get_document_pdf(
    document_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """返回受控 PDF 流，支持 HTTP Range（单块 206 与多块 multipart/byteranges）。

    PDF.js 客户端默认用 Range 请求分块加载大文件；后端支持 Range 时按需
    返回 206 块，避免整包下载。无 Range 头时回退完整文件（200）。
    """
    path = await DocumentPreviewService(session).get_pdf_path(document_id)
    file_size = path.stat().st_size
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
        "Accept-Ranges": "bytes",
        "Content-Type": "application/pdf",
        "Content-Disposition": f'inline; filename="{path.name}"',
    }

    range_header = request.headers.get("range")
    if not range_header or not range_header.startswith("bytes="):
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=path.name,
            content_disposition_type="inline",
            headers=headers,
        )

    # 解析 Range 头：支持单块 "bytes=start-end" 与多块 "bytes=a-b,c-d"。
    ranges: list[tuple[int, int]] = []
    for part in range_header.removeprefix("bytes=").split(","):
        part = part.strip()
        if "-" not in part:
            continue
        start_text, end_text = part.split("-", 1)
        try:
            if start_text == "":
                # 后缀范围 "bytes=-N"：最后 N 字节
                suffix = int(end_text)
                if suffix <= 0:
                    continue
                start = max(0, file_size - suffix)
                end = file_size - 1
            else:
                start = int(start_text)
                end = int(end_text) if end_text else file_size - 1
        except ValueError:
            continue
        if start < 0 or start >= file_size:
            continue
        end = min(end, file_size - 1)
        if start > end:
            continue
        ranges.append((start, end))
    if not ranges:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    if len(ranges) == 1:
        start, end = ranges[0]
        end = min(end, start + _CHUNK_LIMIT_BYTES - 1)
        length = end - start + 1

        def _read_chunk() -> bytes:
            # 同步文件读取放到线程池，避免阻塞事件循环（分块最大 1MiB）。
            with open(path, "rb") as file_handle:
                file_handle.seek(start)
                return file_handle.read(length)

        body = await anyio.to_thread.run_sync(_read_chunk)
        return Response(
            content=body,
            status_code=206,
            headers={
                **headers,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(length),
            },
        )

    # 多块：multipart/byteranges。逐块读取（每块受上限约束）。
    boundary = "rag-medicine-pdf-range"
    parts: list[bytes] = []
    for start, end in ranges:
        end = min(end, start + _CHUNK_LIMIT_BYTES - 1)
        length = end - start + 1

        def _read_part(part_start: int = start, part_end: int = end) -> bytes:
            # 多块场景同样走线程池读取，避免阻塞事件循环。
            with open(path, "rb") as file_handle:
                file_handle.seek(part_start)
                return file_handle.read(part_end - part_start + 1)

        body = await anyio.to_thread.run_sync(_read_part)
        parts.append(
            b"--" + boundary.encode()
            + b"\r\nContent-Type: application/pdf\r\n"
            + f"Content-Range: bytes {start}-{end}/{file_size}\r\n\r\n".encode()
            + body + b"\r\n"
        )
    parts.append(b"--" + boundary.encode() + b"--\r\n")
    return Response(
        content=b"".join(parts),
        status_code=206,
        headers={
            **headers,
            "Content-Type": f"multipart/byteranges; boundary={boundary}",
        },
    )
