from app.integrations.scispacy_client import SciSpacyClient


def test_missing_optional_dependency_returns_no_entities(monkeypatch):
    client = SciSpacyClient("missing")
    monkeypatch.setattr("app.integrations.scispacy_client.find_spec", lambda _: None)
    assert client.available is False and client.extract("lung cancer") == []
