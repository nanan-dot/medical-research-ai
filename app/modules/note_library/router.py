"""FastAPI transport boundary for the note library."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.note_library.schema import (
    ActorRequest,
    AISuggestionAdopt,
    AISuggestionCreate,
    AISuggestionRead,
    DerivationCreate,
    DerivationRead,
    DraftRead,
    DraftUpdate,
    ExportRead,
    ExportRequest,
    FacetsRead,
    LegacyBackfillRead,
    MetadataPatch,
    NoteCreate,
    NoteListRead,
    NoteListView,
    NoteRead,
    RestoreRequest,
    RevisionCommit,
    RevisionHistoryRead,
    RevisionRead,
)
from app.modules.note_library.service import NoteLibraryService

router = APIRouter(prefix="/note-library", tags=["note-library"])


@router.post("/notes", response_model=NoteRead, status_code=201)
async def create_note(
    payload: NoteCreate, session: AsyncSession = Depends(get_session)
) -> NoteRead:
    return await NoteLibraryService(session).create(payload)


@router.get("/notes", response_model=NoteListRead)
async def list_notes(
    actor_scope: str = Query(min_length=1, max_length=128),
    query: str = Query(default="", max_length=500),
    tags: list[str] | None = Query(default=None),
    research_context_ids: list[int] | None = Query(default=None),
    favorite: bool | None = None,
    archived: bool = False,
    view: NoteListView = "all",
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> NoteListRead:
    return await NoteLibraryService(session).list_notes(
        actor_scope,
        query=query,
        tags=tags,
        research_context_ids=research_context_ids,
        favorite=favorite,
        archived=archived,
        view=view,
        page=page,
        page_size=page_size,
    )


@router.get("/facets", response_model=FacetsRead)
async def facets(
    actor_scope: str = Query(min_length=1, max_length=128),
    query: str = "",
    tags: list[str] | None = Query(default=None),
    research_context_ids: list[int] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> FacetsRead:
    return await NoteLibraryService(session).facets(
        actor_scope, query=query, tags=tags, research_context_ids=research_context_ids
    )


@router.get("/notes/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: int, actor_scope: str, session: AsyncSession = Depends(get_session)
) -> NoteRead:
    return await NoteLibraryService(session).read(note_id, actor_scope)


@router.get("/notes/{note_id}/draft", response_model=DraftRead)
async def get_draft(
    note_id: int, actor_scope: str, session: AsyncSession = Depends(get_session)
) -> DraftRead:
    return await NoteLibraryService(session).get_draft(note_id, actor_scope)


@router.put("/notes/{note_id}/draft", response_model=DraftRead)
async def update_draft(
    note_id: int, payload: DraftUpdate, session: AsyncSession = Depends(get_session)
) -> DraftRead:
    return await NoteLibraryService(session).update_draft(note_id, payload)


@router.post("/notes/{note_id}/revisions", response_model=RevisionRead, status_code=201)
async def commit_revision(
    note_id: int, payload: RevisionCommit, session: AsyncSession = Depends(get_session)
) -> RevisionRead:
    return await NoteLibraryService(session).commit(note_id, payload)


@router.get("/notes/{note_id}/revisions", response_model=RevisionHistoryRead)
async def revision_history(
    note_id: int,
    actor_scope: str,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> RevisionHistoryRead:
    return await NoteLibraryService(session).revision_history(
        note_id, actor_scope, page=page, page_size=page_size
    )


@router.get("/notes/{note_id}/revisions/{revision_no}", response_model=RevisionRead)
async def get_revision(
    note_id: int,
    revision_no: int,
    actor_scope: str,
    session: AsyncSession = Depends(get_session),
) -> RevisionRead:
    return await NoteLibraryService(session).get_revision(
        note_id, revision_no, actor_scope
    )


@router.post("/notes/{note_id}/restore", response_model=RevisionRead, status_code=201)
async def restore(
    note_id: int, payload: RestoreRequest, session: AsyncSession = Depends(get_session)
) -> RevisionRead:
    return await NoteLibraryService(session).restore(note_id, payload)


@router.patch("/notes/{note_id}/metadata", response_model=NoteRead)
async def patch_metadata(
    note_id: int, payload: MetadataPatch, session: AsyncSession = Depends(get_session)
) -> NoteRead:
    return await NoteLibraryService(session).patch_metadata(note_id, payload)


@router.post("/notes/{note_id}/archive", response_model=NoteRead)
async def archive(
    note_id: int, payload: ActorRequest, session: AsyncSession = Depends(get_session)
) -> NoteRead:
    return await NoteLibraryService(session).archive(note_id, payload.actor_scope, True)


@router.post("/notes/{note_id}/unarchive", response_model=NoteRead)
async def unarchive(
    note_id: int, payload: ActorRequest, session: AsyncSession = Depends(get_session)
) -> NoteRead:
    return await NoteLibraryService(session).archive(
        note_id, payload.actor_scope, False
    )


@router.post(
    "/notes/{note_id}/ai-suggestions", response_model=AISuggestionRead, status_code=202
)
async def create_suggestion(
    note_id: int,
    payload: AISuggestionCreate,
    session: AsyncSession = Depends(get_session),
) -> AISuggestionRead:
    return await NoteLibraryService(session).create_suggestion(note_id, payload)


@router.get("/ai-suggestions/{suggestion_id}", response_model=AISuggestionRead)
async def get_suggestion(
    suggestion_id: int, actor_scope: str, session: AsyncSession = Depends(get_session)
) -> AISuggestionRead:
    return await NoteLibraryService(session).suggestion(suggestion_id, actor_scope)


@router.post("/ai-suggestions/{suggestion_id}/cancel", response_model=AISuggestionRead)
async def cancel_suggestion(
    suggestion_id: int,
    payload: ActorRequest,
    session: AsyncSession = Depends(get_session),
) -> AISuggestionRead:
    return await NoteLibraryService(session).cancel_suggestion(
        suggestion_id, payload.actor_scope
    )


@router.post("/ai-suggestions/{suggestion_id}/adopt", response_model=DraftRead)
async def adopt_suggestion(
    suggestion_id: int,
    payload: AISuggestionAdopt,
    session: AsyncSession = Depends(get_session),
) -> DraftRead:
    return await NoteLibraryService(session).adopt_suggestion(suggestion_id, payload)


@router.post(
    "/notes/{note_id}/derivations", response_model=DerivationRead, status_code=201
)
async def derive(
    note_id: int,
    payload: DerivationCreate,
    session: AsyncSession = Depends(get_session),
) -> DerivationRead:
    return await NoteLibraryService(session).derive(note_id, payload)


@router.post("/exports", response_model=ExportRead)
async def export_note(
    payload: ExportRequest, session: AsyncSession = Depends(get_session)
) -> ExportRead:
    return await NoteLibraryService(session).export(payload)


@router.post("/legacy-backfill", response_model=LegacyBackfillRead)
async def backfill_legacy(
    actor_scope: str, dry_run: bool = True, session: AsyncSession = Depends(get_session)
) -> LegacyBackfillRead:
    return await NoteLibraryService(session).backfill_legacy(
        actor_scope, dry_run=dry_run
    )
