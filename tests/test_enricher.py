import json

import httpx
import respx
from sqlalchemy import select

from app.config import settings
from app.enricher import run_enrichment
from app.models import Item


def _payload(first: str, last: str) -> dict:
    return {
        "firstName": first,
        "lastName": last,
        "phone": "+1 555-000-0000",
        "email": f"{first.lower()}@example.com",
        "age": 30,
        "address": {"city": "Phoenix"},
    }


@respx.mock
def test_run_enrichment_processes_pending_items(session):
    session.add_all([Item(key="1", status="pending"), Item(key="2", status="pending")])
    session.commit()

    base = settings.api_base_url
    respx.get(f"{base}/users/1").mock(
        return_value=httpx.Response(200, json=_payload("Emily", "Johnson"))
    )
    respx.get(f"{base}/users/2").mock(
        return_value=httpx.Response(200, json=_payload("Michael", "Williams"))
    )

    processed, failed = run_enrichment()

    assert (processed, failed) == (2, 0)
    session.expire_all()
    items = list(session.scalars(select(Item).order_by(Item.id)))
    assert [i.status for i in items] == ["processed", "processed"]
    info_first = json.loads(items[0].additional_info)
    assert info_first["firstName"] == "Emily"
    assert info_first["city"] == "Phoenix"
    assert info_first["phone"] == "+1 555-000-0000"


@respx.mock
def test_run_enrichment_continues_after_api_error(session):
    session.add_all([Item(key="1", status="pending"), Item(key="2", status="pending")])
    session.commit()

    base = settings.api_base_url
    respx.get(f"{base}/users/1").mock(return_value=httpx.Response(500))
    respx.get(f"{base}/users/2").mock(
        return_value=httpx.Response(200, json=_payload("Michael", "Williams"))
    )

    processed, failed = run_enrichment()

    assert processed == 1
    assert failed == 1
    session.expire_all()
    items = list(session.scalars(select(Item).order_by(Item.id)))
    assert items[0].status == "pending"
    assert items[0].additional_info is None
    assert items[1].status == "processed"
    assert json.loads(items[1].additional_info)["firstName"] == "Michael"


def test_run_enrichment_no_pending_returns_zero(session):
    processed, failed = run_enrichment()
    assert (processed, failed) == (0, 0)
