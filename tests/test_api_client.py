import httpx
import respx

from app.api_client import SubscriberDirectoryClient, _phone_to_user_id

_BASE = "http://test-api"


@respx.mock
def test_fetch_subscriber_success():
    phone = "+79161234567"
    user_id = _phone_to_user_id(phone)
    respx.get(f"{_BASE}/users/{user_id}").mock(
        return_value=httpx.Response(
            200, json={"id": user_id, "firstName": "Emily", "lastName": "Johnson"}
        )
    )
    with SubscriberDirectoryClient(base_url=_BASE) as client:
        result = client.fetch_subscriber(phone)

    assert result["firstName"] == "Emily"


@respx.mock
def test_fetch_subscriber_404_returns_none():
    phone = "+79991112233"
    user_id = _phone_to_user_id(phone)
    respx.get(f"{_BASE}/users/{user_id}").mock(return_value=httpx.Response(404))
    with SubscriberDirectoryClient(base_url=_BASE) as client:
        assert client.fetch_subscriber(phone) is None


@respx.mock
def test_fetch_subscriber_connect_error_returns_none():
    phone = "+79161234567"
    user_id = _phone_to_user_id(phone)
    respx.get(f"{_BASE}/users/{user_id}").mock(side_effect=httpx.ConnectError("boom"))
    with SubscriberDirectoryClient(base_url=_BASE) as client:
        assert client.fetch_subscriber(phone) is None


def test_phone_to_user_id_is_deterministic_and_in_range():
    phone = "+79161234567"
    assert _phone_to_user_id(phone) == _phone_to_user_id(phone)
    for p in ["+79991112233", "+79257654321", "+79160000000"]:
        assert 1 <= _phone_to_user_id(p) <= 208
