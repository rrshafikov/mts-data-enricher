import json

import httpx
import respx
from sqlalchemy import select

from app.api_client import _phone_to_user_id
from app.config import settings
from app.enricher import run_enrichment
from app.models import Item


def _payload(first: str, last: str) -> dict:
    return {
        "firstName": first,
        "lastName": last,
        "email": f"{first.lower()}@example.com",
        "age": 30,
        "address": {"city": "Phoenix"},
        "company": {"name": "Acme Inc"},
    }


@respx.mock
def test_run_enrichment_processes_pending_items(session):
    p1, p2 = "+79161234567", "+79257654321"
    session.add_all([Item(key=p1, status="pending"), Item(key=p2, status="pending")])
    session.commit()

    base = settings.api_base_url
    respx.get(f"{base}/users/{_phone_to_user_id(p1)}").mock(
        return_value=httpx.Response(200, json=_payload("Emily", "Johnson"))
    )
    respx.get(f"{base}/users/{_phone_to_user_id(p2)}").mock(
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
    assert "company" not in info_first


@respx.mock
def test_run_enrichment_continues_after_api_error(session):
    p1, p2 = "+79161234567", "+79257654321"
    session.add_all([Item(key=p1, status="pending"), Item(key=p2, status="pending")])
    session.commit()

    base = settings.api_base_url
    respx.get(f"{base}/users/{_phone_to_user_id(p1)}").mock(return_value=httpx.Response(500))
    respx.get(f"{base}/users/{_phone_to_user_id(p2)}").mock(
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
