import httpx
import respx

from app.api_client import SubscriberDirectoryClient

_BASE = "http://test-api"


@respx.mock
def test_fetch_subscriber_success(monkeypatch):
    monkeypatch.setattr("app.api_client.settings.api_path", "/users/{key}")
    respx.get(f"{_BASE}/users/1").mock(
        return_value=httpx.Response(
            200, json={"id": 1, "firstName": "Emily", "lastName": "Johnson"}
        )
    )
    with SubscriberDirectoryClient(base_url=_BASE) as client:
        result = client.fetch_subscriber(1)

    assert result["firstName"] == "Emily"


@respx.mock
def test_fetch_subscriber_404_returns_none(monkeypatch):
    monkeypatch.setattr("app.api_client.settings.api_path", "/users/{key}")
    respx.get(f"{_BASE}/users/999").mock(return_value=httpx.Response(404))
    with SubscriberDirectoryClient(base_url=_BASE) as client:
        assert client.fetch_subscriber(999) is None


@respx.mock
def test_fetch_subscriber_connect_error_returns_none(monkeypatch):
    monkeypatch.setattr("app.api_client.settings.api_path", "/users/{key}")
    respx.get(f"{_BASE}/users/1").mock(side_effect=httpx.ConnectError("boom"))
    with SubscriberDirectoryClient(base_url=_BASE) as client:
        assert client.fetch_subscriber(1) is None
