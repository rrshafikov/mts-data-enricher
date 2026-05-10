import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app import db
from app.config import settings
from app.enricher import run_enrichment
from app.logging_setup import setup_logging
from app.models import Item
from app.seed import add_pending

setup_logging(settings.log_level)

_BASE = Path(__file__).parent

app = FastAPI(title="MTS Data Enricher")
app.mount("/static", StaticFiles(directory=_BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(_BASE / "templates"))


def _parse_info(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


@app.get("/")
def index(request: Request, processed: int | None = None, failed: int | None = None):
    with db.SessionLocal() as session:
        items = list(session.scalars(select(Item).order_by(Item.id)))

    rows = [
        {
            "id": item.id,
            "key": item.key,
            "status": item.status,
            "info": _parse_info(item.additional_info),
            "raw_info": item.additional_info,
        }
        for item in items
    ]
    pending_count = sum(1 for i in items if i.status == "pending")
    processed_count = sum(1 for i in items if i.status == "processed")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "rows": rows,
            "total": len(items),
            "pending": pending_count,
            "processed": processed_count,
            "last_processed": processed,
            "last_failed": failed,
        },
    )


_MAX_SEED_PER_REQUEST = 100


@app.post("/seed")
def seed_endpoint(count: int = Form(5)):
    # Серверная валидация: HTML-input ограничен max=50, но это легко обойти
    # ручным curl. Бьём по верхней границе явно, чтобы не положить БД.
    if not 1 <= count <= _MAX_SEED_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"count must be between 1 and {_MAX_SEED_PER_REQUEST}",
        )
    add_pending(count)
    return RedirectResponse("/", status_code=303)


@app.post("/enrich")
def enrich_endpoint():
    processed, failed = run_enrichment()
    return RedirectResponse(f"/?processed={processed}&failed={failed}", status_code=303)
