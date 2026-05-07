import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import db
from app.api_client import JSONPlaceholderClient
from app.config import settings
from app.models import Item

logger = logging.getLogger(__name__)


def _extract_additional_info(payload: dict[str, Any]) -> str:
    """Достаём `body` из ответа JSONPlaceholder; если поля нет — сохраняем весь JSON."""
    body = payload.get("body")
    if isinstance(body, str):
        return body
    return json.dumps(payload, ensure_ascii=False)


def _fetch_pending_batch(
    session: Session, limit: int, skip_ids: set[int]
) -> list[Item]:
    stmt = select(Item).where(Item.status == "pending")
    if skip_ids:
        stmt = stmt.where(Item.id.notin_(skip_ids))
    stmt = stmt.order_by(Item.id).limit(limit)
    return list(session.scalars(stmt))


def run_enrichment(batch_size: int | None = None) -> tuple[int, int]:
    """Обработать все pending-записи.

    На каждую запись:
      1. Делаем запрос к API.
      2. Если ответ получен — сохраняем `body` в `additional_info`,
         меняем `status` на `processed`, коммитим.
      3. При любой ошибке (API/БД) логгируем и идём дальше — запись
         попадёт в skip_ids, чтобы не зациклиться в текущем запуске.
         На следующем запуске её снова попробуют обработать.

    Returns:
        (processed, failed) — счётчики успешно обработанных и проваленных.
    """
    batch_size = batch_size or settings.batch_size
    processed = 0
    failed = 0
    skip_ids: set[int] = set()

    with JSONPlaceholderClient() as client, db.SessionLocal() as session:
        while True:
            items = _fetch_pending_batch(session, batch_size, skip_ids)
            if not items:
                break

            for item in items:
                payload = client.fetch_post(item.key)
                if payload is None:
                    failed += 1
                    skip_ids.add(item.id)
                    continue

                try:
                    item.additional_info = _extract_additional_info(payload)
                    item.status = "processed"
                    session.commit()
                except SQLAlchemyError:
                    session.rollback()
                    failed += 1
                    skip_ids.add(item.id)
                    logger.exception("DB error while saving item id=%s", item.id)
                    continue

                processed += 1
                logger.info("Item id=%s key=%s processed", item.id, item.key)

    logger.info("Enrichment finished: processed=%d failed=%d", processed, failed)
    return processed, failed
