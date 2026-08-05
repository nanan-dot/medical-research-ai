"""Markdown 笔记切片：标题切片 + 固定长度回退。

设计意图：
- 标题切片优先：保留语义边界，每个块可溯源到具体标题；
- 超长标题段回退到固定长度切片（重叠可选），避免单块过大；
- 无标题正文作为独立一块（空文本由 ``Chunk.validate_text`` 拦截）；
- ``chunk_id`` 使用文档内全局递增序号，避免多个标题块各自从 0 开始造成冲突。
"""

import re

from app.rag.schemas import Chunk, SplitStrategy

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

# 无标题正文使用的占位标题
UNTITLED_HEADING = ""


def split_markdown_document(
    content: str,
    *,
    document_id: str,
    source_path: str = "",
    strategy: SplitStrategy | None = None,
) -> list[Chunk]:
    """把 Markdown 文本切成可检索的分块。

    :param content: Markdown 原文
    :param document_id: 文档唯一标识（如文件名或哈希）
    :param source_path: 来源文件路径，用于可解释引用
    :param strategy: 切片策略，默认标题切片
    :return: 按出现顺序排列的分块
    """
    splitter = SplitStrategy() if strategy is None else strategy
    if splitter.mode == "fixed_length":
        return _fixed_length_chunks(
            content,
            document_id=document_id,
            source_path=source_path,
            strategy=splitter,
            heading=UNTITLED_HEADING,
        )

    chunks: list[Chunk] = []
    chunk_index = 0
    for heading, text in _iter_heading_blocks(content):
        produced = _fixed_length_chunks(
            text,
            document_id=document_id,
            source_path=source_path,
            strategy=splitter,
            heading=heading,
            chunk_index_start=chunk_index,
        )
        chunk_index += len(produced)
        chunks.extend(produced)
    return chunks


def _iter_heading_blocks(content: str) -> list[tuple[str, str]]:
    """把 Markdown 按标题切成分组，返回 ``(heading, 组内正文)`` 列表。

    - 标题行本身不出现在正文中；
    - 文件开头的无标题段落归入 ``UNTITLED_HEADING``；
    - 标题层级（1~6）不参与排序，只作为块边界。
    """
    blocks: list[tuple[str, str]] = []
    current_heading = UNTITLED_HEADING
    current_lines: list[str] = []
    for line in content.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            blocks.append((current_heading, "\n".join(current_lines)))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    blocks.append((current_heading, "\n".join(current_lines)))
    return blocks


def _fixed_length_chunks(
    text: str,
    *,
    document_id: str,
    source_path: str,
    strategy: SplitStrategy,
    heading: str = UNTITLED_HEADING,
    chunk_index_start: int = 0,
) -> list[Chunk]:
    """按固定长度切片（重叠可选），并组装成带文档内全局序号的块。

    单块未超限时同样走此函数：只会产出 1 块，等价于标题切片的常规语义。
    """
    text = text.strip()
    if not text:
        return []

    chunk_size = strategy.chunk_size
    # 重叠最大收敛到 chunk_size-1，保证滑动步长至少为 1，避免死循环或近乎重复的块
    overlap = min(strategy.overlap, chunk_size - 1)
    step = max(chunk_size - overlap, 1)

    chunks: list[Chunk] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        piece = text[start : start + chunk_size]
        if piece.strip():
            chunk = Chunk(
                chunk_id=f"{document_id}:{chunk_index_start + len(chunks)}",
                document_id=document_id,
                heading=heading,
                text=piece,
                source_path=source_path,
            )
            chunk.validate_text()
            chunks.append(chunk)
        start += step
    return chunks
