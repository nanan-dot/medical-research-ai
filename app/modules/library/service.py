"""Business orchestration for library browsing, access, and storage."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.document.schema import (
    DocumentFileType,
    DocumentHealthStatus,
    DocumentRead,
)
from app.modules.document.task_service import DocumentTaskService
from app.modules.library.model import DocumentAccess
from app.modules.library.repository import LibraryQuery, LibraryRepository
from app.modules.library.schema import (
    DocumentOpenedRead,
    LibraryFacets,
    LibraryFacetValue,
    LibraryHealthStatus,
    LibraryIssueBreakdown,
    LibraryItemPage,
    LibraryItemRead,
    LibrarySourceTree,
    LibrarySourceTreeGroup,
    LibrarySourceTreeNode,
    LibrarySourceType,
    LibrarySourceTypeCount,
    LibraryStorageSummary,
    LibrarySummary,
)
from app.modules.task.model import TaskRecord


class LibraryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = LibraryRepository(session)

    async def summary(self) -> LibrarySummary:
        values = await self._repository.summary_values()
        return LibrarySummary(
            total=values["total"], processed=values["processed"],
            ai_available=values["ai_available"], processing=values["processing"],
            needs_attention=values["needs_attention"],
            issue_breakdown=LibraryIssueBreakdown(**{key: values[key] for key in LibraryIssueBreakdown.model_fields}),
            source_types=[LibrarySourceTypeCount(source_type=LibrarySourceType(kind), count=count) for kind, count in await self._repository.source_type_counts()],
            snapshot_at=datetime.now(UTC),
        )

    async def page(self, query: LibraryQuery, sort_by: str, sort_order: str, offset: int, limit: int) -> LibraryItemPage:
        documents = await self._repository.list_documents(query, sort_by, sort_order, offset, limit)
        accesses = await self._repository.access_by_document_ids([document.id for document in documents])
        tasks = await self._active_tasks([document.id for document in documents])
        return LibraryItemPage(
            items=[self._to_item(document, accesses.get(document.id), tasks.get(document.id), query.q) for document in documents],
            total=await self._repository.count_documents(query), offset=offset, limit=limit,
        )

    async def item(self, document_id: int) -> LibraryItemRead:
        document = await self._require_document(document_id)
        access = (await self._repository.access_by_document_ids([document_id])).get(document_id)
        task = (await self._active_tasks([document_id])).get(document_id)
        return self._to_item(document, access, task, None)

    async def facets(self, query: LibraryQuery) -> LibraryFacets:
        values = await self._repository.facets(query)
        return LibraryFacets(**{name: [LibraryFacetValue(value=value, count=count) for value, count in rows] for name, rows in values.items()})

    async def opened(self, document_id: int, actor_id: str | None, key: str | None) -> DocumentOpenedRead:
        await self._require_document(document_id)
        access = (await self._repository.access_by_document_ids([document_id])).get(document_id)
        now = datetime.now(UTC)
        if access is None:
            access = DocumentAccess(document_id=document_id, last_opened_at=now, last_opened_by=actor_id, open_count=1, last_open_request_key=key)
            self._session.add(access)
        elif not key or access.last_open_request_key != key:
            access.last_opened_at = now
            access.last_opened_by = actor_id
            access.open_count += 1
            access.last_open_request_key = key
        await self._session.flush()
        return DocumentOpenedRead(document_id=document_id, last_opened_at=access.last_opened_at, last_opened_by=access.last_opened_by, open_count=access.open_count)

    async def recent(self, offset: int, limit: int) -> LibraryItemPage:
        documents = await self._repository.list_recent_documents(offset, limit)
        accesses = await self._repository.access_by_document_ids(
            [document.id for document in documents]
        )
        tasks = await self._active_tasks([document.id for document in documents])
        return LibraryItemPage(
            items=[
                self._to_item(document, accesses.get(document.id), tasks.get(document.id), None)
                for document in documents
            ],
            total=await self._repository.count_recent_documents(),
            offset=offset,
            limit=limit,
        )

    async def storage(self, quota_bytes: int | None) -> LibraryStorageSummary:
        managed, external = await self._repository.storage_values()
        total = managed + external
        status = "not_configured" if quota_bytes is None else ("exceeded" if managed > quota_bytes else "within_quota")
        percent = None if quota_bytes is None else round(managed * 100 / quota_bytes, 2) if quota_bytes else 100.0
        return LibraryStorageSummary(managed_bytes=managed, external_source_bytes=external, total_known_bytes=total, quota_bytes=quota_bytes, usage_percent=percent, status=status, measured_at=datetime.now(UTC))

    async def tree(self) -> LibrarySourceTree:
        documents = await self._repository.documents_for_tree()
        sources = await self._repository.source_rows()
        zotero_collections = await self._repository.zotero_collections_by_source()
        roots: dict[str, LibrarySourceTreeGroup] = {kind: LibrarySourceTreeGroup(source_type=kind, node_id=f"group:{kind}") for kind in ("local", "obsidian", "zotero")}
        source_nodes: dict[int, LibrarySourceTreeNode] = {}
        for source_row in sources:
            group_key = {
                "local_folder": "local",
                "obsidian_vault": "obsidian",
                "zotero_library": "zotero",
            }.get(source_row.source_type)
            if group_key is None:
                continue
            node = LibrarySourceTreeNode(
                node_id=f"source:{source_row.id}",
                parent_id=roots[group_key].node_id,
                name=source_row.name,
                source_id=source_row.id,
                health="ready" if source_row.sync_status != "unavailable" else "unavailable",
            )
            source_nodes[source_row.id] = node
            roots[group_key].children.append(node)
        for source_id, collections in zotero_collections.items():
            source_node = source_nodes.get(source_id)
            if source_node is None:
                continue
            by_key: dict[str, LibrarySourceTreeNode] = {}
            pending = list(collections)
            while pending:
                progressed = False
                for collection in pending[:]:
                    parent = by_key.get(collection.parent_key or "", source_node)
                    if collection.parent_key and collection.parent_key not in by_key:
                        continue
                    node = LibrarySourceTreeNode(
                        node_id=f"zotero-collection:{source_id}:{collection.collection_key}",
                        parent_id=parent.node_id,
                        name=collection.name,
                        relative_path=collection.collection_key,
                        source_id=source_id,
                        health="ready",
                    )
                    parent.children.append(node)
                    by_key[collection.collection_key] = node
                    pending.remove(collection)
                    progressed = True
                if not progressed:
                    # A remote parent can be missing in an incremental page; retain
                    # the child visibly under the source rather than dropping it.
                    collection = pending.pop(0)
                    node = LibrarySourceTreeNode(
                        node_id=f"zotero-collection:{source_id}:{collection.collection_key}",
                        parent_id=source_node.node_id,
                        name=collection.name,
                        relative_path=collection.collection_key,
                        source_id=source_id,
                        health="degraded",
                    )
                    source_node.children.append(node)
                    by_key[collection.collection_key] = node
        for document in documents:
            document_source = document.source
            assert document_source is not None
            group_key = {"local_folder": "local", "obsidian_vault": "obsidian", "zotero_library": "zotero"}.get(document_source.source_type, "local")
            group = roots[group_key]
            document_node = source_nodes.get(document_source.id)
            if document_node is None:
                document_node = LibrarySourceTreeNode(node_id=f"source:{document_source.id}", parent_id=group.node_id, name=document_source.name, source_id=document_source.id, health="ready")
                source_nodes[document_source.id] = document_node
                group.children.append(document_node)
            parts = [part for part in document.normalized_file_path.replace("\\", "/").split("/")[:-1] if part]
            parent = document_node
            current_path = ""
            for part in parts:
                current_path = f"{current_path}/{part}".strip("/")
                child = next((value for value in parent.children if value.name.casefold() == part.casefold()), None)
                if child is None:
                    child = LibrarySourceTreeNode(node_id=f"tree:{document_source.id}:{current_path}", parent_id=parent.node_id, name=part, relative_path=current_path, source_id=document_source.id, health="ready")
                    parent.children.append(child)
                parent = child
            parent.direct_count += 1
            for ancestor in [document_node, *self._ancestor_nodes(document_node, parts)]:
                ancestor.descendant_count += 1
            group.descendant_count += 1
        return LibrarySourceTree(groups=list(roots.values()))

    @staticmethod
    def _ancestor_nodes(source: LibrarySourceTreeNode, parts: list[str]) -> list[LibrarySourceTreeNode]:
        nodes: list[LibrarySourceTreeNode] = []
        current = source
        for part in parts:
            current = next(child for child in current.children if child.name.casefold() == part.casefold())
            nodes.append(current)
        return nodes

    async def enqueue(self, document_id: int, operation: str) -> TaskRecord:
        await self._require_document(document_id)
        return await DocumentTaskService(self._session).enqueue(document_id, operation)

    async def _require_document(self, document_id: int):
        document = await self._repository.get_document(document_id)
        if document is None:
            raise NotFoundError("Document not found")
        return document

    async def _active_tasks(self, document_ids: list[int]) -> dict[int, TaskRecord]:
        if not document_ids:
            return {}
        rows = await self._session.execute(
            select(TaskRecord).where(TaskRecord.source_type == "document", TaskRecord.source_id.in_(document_ids), TaskRecord.status.in_(("queued", "running"))).order_by(TaskRecord.created_at.desc(), TaskRecord.id.desc())
        )
        result: dict[int, TaskRecord] = {}
        for task in rows.scalars():
            if task.source_id is not None:
                result.setdefault(task.source_id, task)
        return result

    @staticmethod
    def _status(document) -> LibraryHealthStatus:
        if document.parse_status == "failed" or document.index_status == "failed" or document.error_code:
            return LibraryHealthStatus.NEEDS_ATTENTION
        if document.index_status == "outdated" or document.scan_state == "outdated":
            return LibraryHealthStatus.OUTDATED
        if document.metadata_only:
            return LibraryHealthStatus.METADATA_ONLY
        if document.parse_status == "succeeded" and document.index_status == "succeeded" and document.paperqa_index_key:
            return LibraryHealthStatus.AI_AVAILABLE
        return LibraryHealthStatus.PROCESSING

    def _to_item(self, document, access: DocumentAccess | None, task: TaskRecord | None, query: str | None) -> LibraryItemRead:
        source = document.source
        assert source is not None
        name = document.original_filename or Path(document.file_path).name
        file_type = DocumentFileType.MARKDOWN if name.casefold().endswith((".md", ".markdown")) else DocumentFileType(Path(name).suffix.casefold().lstrip(".")) if Path(name).suffix.casefold().lstrip(".") in DocumentFileType._value2member_map_ else DocumentFileType.OTHER
        status = self._status(document)
        match_fields = []
        snippet = None
        if query:
            needle = query.casefold()
            if needle in name.casefold(): match_fields.append("name")
            if needle in document.file_path.casefold(): match_fields.append("path")
            if needle in source.name.casefold(): match_fields.append("source")
            if needle in (document.parsed_content or "").casefold():
                match_fields.append("content")
                text = document.parsed_content or ""
                position = text.casefold().find(needle)
                snippet = " ".join(text[max(0, position - 80): position + len(query) + 80].split())
        actions = ["view", "delete"]
        if task: actions.append("view_progress")
        if status in {LibraryHealthStatus.NEEDS_ATTENTION, LibraryHealthStatus.OUTDATED}: actions.extend(["repair", "reprocess"])
        return LibraryItemRead.model_validate(DocumentRead.model_validate(document).model_copy(update={
            "source_name": source.name, "source_type": source.source_type, "relative_path": document.file_path.replace("\\", "/"), "display_name": name,
            "file_type": file_type, "preview_capability": file_type in {DocumentFileType.PDF, DocumentFileType.DOCX}, "health_status": DocumentHealthStatus.AVAILABLE if status == LibraryHealthStatus.AI_AVAILABLE else (DocumentHealthStatus.NEEDS_ATTENTION if status in {LibraryHealthStatus.NEEDS_ATTENTION, LibraryHealthStatus.OUTDATED, LibraryHealthStatus.METADATA_ONLY} else DocumentHealthStatus.PROCESSING),
            "available_actions": actions, "task_id": task.id if task else None, "task_status": task.status if task else None, "progress": task.progress if task else None, "phase": task.phase if task else None, "current_item": task.current_item if task else None, "last_opened_at": access.last_opened_at if access else None, "open_count": access.open_count if access else 0,
        }).model_dump() | {"status": status, "match_fields": match_fields, "snippet": snippet, "locator": None})
