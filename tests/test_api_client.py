import httpx
import respx

from app.api_client import JSONPlaceholderClient


@respx.mock
def test_fetch_post_success():
    respx.get("https://jsonplaceholder.typicode.com/posts/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "body": "text"})
    )
    with JSONPlaceholderClient() as client:
        result = client.fetch_post(1)

    assert result == {"id": 1, "body": "text"}


@respx.mock
def test_fetch_post_404_returns_none():
    respx.get("https://jsonplaceholder.typicode.com/posts/999").mock(
        return_value=httpx.Response(404)
    )
    with JSONPlaceholderClient() as client:
        assert client.fetch_post(999) is None


@respx.mock
def test_fetch_post_connect_error_returns_none():
    respx.get("https://jsonplaceholder.typicode.com/posts/1").mock(
        side_effect=httpx.ConnectError("boom")
    )
    with JSONPlaceholderClient() as client:
        assert client.fetch_post(1) is None
