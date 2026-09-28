"""A3 relocation API acceptance tests."""


def _create_anchored_annotation(selection_client):
    api, document_id, _, descriptor = selection_client
    response = api.post(
        f"/api/v1/documents/{document_id}/annotations",
        headers={"Idempotency-Key": "a3-annotation"},
        json={"anchor_descriptor": descriptor, "color": "yellow", "note": "keep"},
    )
    assert response.status_code == 201, response.text
    return response.json(), descriptor


def test_candidates_are_proposed_and_never_auto_confirmed(selection_client) -> None:
    api, _, _, descriptor = selection_client
    annotation, _ = _create_anchored_annotation(selection_client)
    response = api.post(
        f"/api/v1/source-anchors/{annotation['source_anchor_id']}/relocation-candidates",
        json={"target_anchor_revision_id": descriptor["expected_anchor_revision_id"]},
    )
    assert response.status_code == 201, response.text
    candidates = response.json()
    assert candidates
    assert {row["status"] for row in candidates} == {"proposed"}
    assert all(row["decision_source"] is None for row in candidates)
    assert all("quote" not in row["score_breakdown"] for row in candidates)


def test_human_confirmation_updates_resolved_anchor_with_optimistic_lock(
    selection_client,
) -> None:
    api, _, factory, descriptor = selection_client
    annotation, _ = _create_anchored_annotation(selection_client)
    anchor_id = annotation["source_anchor_id"]
    candidate = api.post(
        f"/api/v1/source-anchors/{anchor_id}/relocation-candidates",
        json={"target_anchor_revision_id": descriptor["expected_anchor_revision_id"]},
    ).json()[0]
    payload = {
        "asset_type": "document_annotation",
        "asset_id": annotation["id"],
        "candidate_id": candidate["id"],
        "decision": "confirm",
        "expected_resolution_version": 1,
        "decision_note": "manually compared",
    }
    confirmed = api.post(
        f"/api/v1/source-anchors/{anchor_id}/relocations/{candidate['id']}/decisions",
        json=payload,
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["original_anchor_id"] == anchor_id
    assert body["resolved_anchor_id"] == candidate["candidate_anchor_id"]
    assert body["resolution_status"] == "relocated_verified"
    assert body["resolution_version"] == 2
    listed = api.get(f"/api/v1/documents/{annotation['document_id']}/annotations")
    assert listed.status_code == 200
    assert listed.json()[0]["source_anchor_id"] == anchor_id
    assert (
        listed.json()[0]["resolved_source_anchor_id"]
        == candidate["candidate_anchor_id"]
    )

    async def audit_count():
        from sqlalchemy import func, select

        from app.modules.document_relocation.model import (
            DocumentAnchorRelocationDecision,
        )

        async with factory() as session:
            return await session.scalar(
                select(func.count()).select_from(DocumentAnchorRelocationDecision)
            )

    import asyncio

    assert asyncio.run(audit_count()) == 1

    stale = api.post(
        f"/api/v1/source-anchors/{anchor_id}/relocations/{candidate['id']}/decisions",
        json=payload,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "RESOLUTION_VERSION_CONFLICT"


def test_candidate_access_is_scoped_to_authorized_document(selection_client) -> None:
    api, _, factory, _ = selection_client
    annotation, descriptor = _create_anchored_annotation(selection_client)

    async def disable_source():

        from app.modules.document.model import Document
        from app.modules.knowledge_source.model import KnowledgeSource

        async with factory() as session:
            document = await session.get(Document, annotation["document_id"])
            source = await session.get(KnowledgeSource, document.knowledge_source_id)
            source.enabled = False
            await session.commit()

    import asyncio

    asyncio.run(disable_source())
    response = api.post(
        f"/api/v1/source-anchors/{annotation['source_anchor_id']}/relocation-candidates",
        json={"target_anchor_revision_id": descriptor["expected_anchor_revision_id"]},
    )
    assert response.status_code == 403
    assert "Dose 5 mg" not in response.text
