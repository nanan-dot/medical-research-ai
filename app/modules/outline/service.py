import json
from datetime import UTC, datetime
from typing import cast
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.exceptions import ConflictError, NotFoundError
from app.modules.evidence_matrix.repository import EvidenceMatrixRepository
from app.modules.research_direction.repository import ResearchDirectionRepository
from app.modules.outline.model import Outline
from app.modules.outline.outline_builder import build_outline
from app.modules.outline.repository import OutlineRepository
from app.modules.outline.schema import OutlineCreate, OutlineKind, OutlineRead


class OutlineService:
    def __init__(self, s: AsyncSession):
        self.r = OutlineRepository(s)
        self.m = EvidenceMatrixRepository(s)
        self.d = ResearchDirectionRepository(s)

    async def create(self, p: OutlineCreate) -> OutlineRead:
        matrix = await self.m.get_matrix(p.matrix_id)
        cells = await self.m.list_cells(p.matrix_id)
        if matrix is None:
            raise NotFoundError("Evidence matrix not found")
        if not cells:
            raise ConflictError("Evidence matrix is empty")
        directions = await self.d.list_for_matrix(p.matrix_id)
        e = Outline(
            matrix_id=p.matrix_id,
            kind=p.kind,
            claims_json=json.dumps(
                [x.model_dump() for x in build_outline(p.kind, cells, [x.name for x in directions])]
            ),
        )
        return self.read(await self.r.create(e))

    async def get(self, id: int) -> OutlineRead:
        e = await self.r.get(id)
        if e is None:
            raise NotFoundError("Outline not found")
        return self.read(e)

    async def confirm(self, id: int) -> OutlineRead:
        e = await self.r.get(id)
        if e is None:
            raise NotFoundError("Outline not found")
        e.confirmed_by_user = True
        e.confirmed_at = datetime.now(UTC)
        return self.read(await self.r.save(e))

    @staticmethod
    def read(e: Outline) -> OutlineRead:
        return OutlineRead(
            id=e.id,
            matrix_id=e.matrix_id,
            kind=cast(OutlineKind, e.kind),
            claims=json.loads(e.claims_json),
            version=e.version,
            confirmed_by_user=e.confirmed_by_user,
            confirmed_at=e.confirmed_at,
            created_at=e.created_at,
        )
