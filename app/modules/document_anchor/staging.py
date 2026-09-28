"""数据库外暂存已校验页面；只保留单页正文在内存中。"""

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import IO, overload

from app.modules.document_anchor.contract import HeaderRecord, PageRecord, TrailerRecord


class StagedPages(Sequence[PageRecord]):
    def __init__(self, file: IO[str], offsets: list[int]) -> None:
        self.file = file
        self.offsets = offsets

    def __len__(self) -> int:
        return len(self.offsets)

    @overload
    def __getitem__(self, index: int) -> PageRecord: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[PageRecord]: ...

    def __getitem__(self, index: int | slice) -> PageRecord | Sequence[PageRecord]:
        if isinstance(index, slice):
            return [self[value] for value in range(*index.indices(len(self)))]
        self.file.seek(self.offsets[index])
        return PageRecord.model_validate(json.loads(self.file.readline()))

    def __iter__(self) -> Iterator[PageRecord]:
        for index in range(len(self)):
            yield self[index]


@dataclass
class StagedExtraction:
    header: HeaderRecord
    pages: StagedPages
    trailer: TrailerRecord
    page_hashes: list[str]
    document_hash: str
    quality_flags: list[list[str]]

    def close(self) -> None:
        self.pages.file.close()
