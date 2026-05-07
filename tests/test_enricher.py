import httpx
import respx
from sqlalchemy import select

from app.enricher import run_enrichment
from app.models import Item


@respx.mock
def test_run_enrichment_processes_pending_items(session):
    session.add_all([Item(key="1", status="pending"), Item(key="2", status="pending")])
    session.commit()

    respx.get("https://jsonplaceholder.typicode.com/posts/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "body": "body-1"})
    )
    respx.get("https://jsonplaceholder.typicode.com/posts/2").mock(
        return_value=httpx.Response(200, json={"id": 2, "body": "body-2"})
    )

    processed, failed = run_enrichment()

    assert (processed, failed) == (2, 0)
    session.expire_all()
    items = list(session.scalars(select(Item).order_by(Item.id)))
    assert [i.status for i in items] == ["processed", "processed"]
    assert [i.additional_info for i in items] == ["body-1", "body-2"]


@respx.mock
def test_run_enrichment_continues_after_api_error(session):
    session.add_all([Item(key="1", status="pending"), Item(key="2", status="pending")])
    session.commit()

    respx.get("https://jsonplaceholder.typicode.com/posts/1").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://jsonplaceholder.typicode.com/posts/2").mock(
        return_value=httpx.Response(200, json={"body": "ok"})
    )

    processed, failed = run_enrichment()

    assert processed == 1
    assert failed == 1
    session.expire_all()
    items = list(session.scalars(select(Item).order_by(Item.id)))
    assert items[0].status == "pending"
    assert items[0].additional_info is None
    assert items[1].status == "processed"
    assert items[1].additional_info == "ok"


def test_run_enrichment_no_pending_returns_zero(session):
    processed, failed = run_enrichment()
    assert (processed, failed) == (0, 0)
