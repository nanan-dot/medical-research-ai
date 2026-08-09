from app.modules.literature_search.status_classifier import classify


def test_unknown_wins_when_metadata_is_not_verified(): assert classify(verified=False, is_retracted=True) == "unknown"
def test_retraction_and_preprint_are_distinct():
    assert classify(verified=True, is_retracted=True) == "retracted"
    assert classify(verified=True, is_preprint=True) == "preprint"
