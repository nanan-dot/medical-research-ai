"""Small acceptance-test helpers for observable note behavior."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.note_library.schema import NoteCreate, RevisionCommit
from app.modules.note_library.service import NoteLibraryService


async def create_committed_note(
    session: AsyncSession,
    *,
    actor: str = "user:test",
    title: str = "Title",
    body: str = "Body",
    key: str = "save-1",
) -> tuple[int, int]:
    service = NoteLibraryService(session)
    note = await service.create(NoteCreate(actor_scope=actor, title=title, body=body))
    revision = await service.commit(
        note.id,
        RevisionCommit(
            actor_scope=actor,
            expected_base_revision=0,
            expected_draft_version=1,
            idempotency_key=key,
        ),
    )
    await session.commit()
    return note.id, revision.id
