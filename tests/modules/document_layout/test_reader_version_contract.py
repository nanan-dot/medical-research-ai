from tests.modules.document_annotation.test_document_annotation_api import client
from tests.modules.document_selection.test_api import selection_client

__all__ = ["client", "selection_client"]


def test_reader_segments_are_version_pinned(selection_client):
    api, document_id, _, descriptor = selection_client
    params = {
        "page": 1,
        "expected_anchor_revision_id": descriptor["expected_anchor_revision_id"],
        "expected_segmentation_revision_id": descriptor["expected_segmentation_revision_id"],
    }
    result = api.get(f"/api/v1/documents/{document_id}/source-segments", params=params)
    assert result.status_code == 200
    assert result.json()["anchor_revision_id"] == params["expected_anchor_revision_id"]
    assert result.json()["segmentation_revision_id"] == params["expected_segmentation_revision_id"]
    for field in ("expected_anchor_revision_id", "expected_segmentation_revision_id"):
        stale = api.get(f"/api/v1/documents/{document_id}/source-segments", params={**params, field: 99999})
        assert stale.status_code == 409
        assert "Dose" not in stale.text
