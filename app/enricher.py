import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import db
from app.api_client import SubscriberDirectoryClient
from app.config import settings
from app.models import Item

logger = logging.getLogger(__name__)


def _extract_additional_info(payload: dict[str, Any]) -> str:
    """Сохраняем подмножество полей профиля абонента как JSON.

    Внешний API отдаёт ~20 полей (включая фото, пароль, день рождения и т.п.).
    Берём только то, что нужно для обогащения.
    """
    address = payload.get("address") or {}
    cleaned = {
        k: v
        for k, v in {
            "firstName": payload.get("firstName"),
            "lastName": payload.get("lastName"),
            "phone": payload.get("phone"),
            "email": payload.get("email"),
            "age": payload.get("age"),
            "city": address.get("city"),
        }.items()
        if v is not None
    }
    if not cleaned:
        return json.dumps(payload, ensure_ascii=False)
    return json.dumps(cleaned, ensure_ascii=False)


def _fetch_pending_batch(session: Session, limit: int, skip_ids: set[int]) -> list[Item]:
    """Тянем очередной батч pending-записей.

    skip_ids исключает строки, которые уже не получилось обработать в этом
    прогоне (API/БД ошибки) — иначе цикл `while pending exists` уходил бы
    в бесконечный повтор тех же провальных записей.
    """
    stmt = select(Item).where(Item.status == "pending")
    if skip_ids:
        stmt = stmt.where(Item.id.notin_(skip_ids))
    stmt = stmt.order_by(Item.id).limit(limit)
    return list(session.scalars(stmt))


def run_enrichment(batch_size: int | None = None) -> tuple[int, int]:
    """Обработать все pending-записи.

    На каждую запись:
      1. Делаем запрос к внешнему справочнику абонентов по `key`.
      2. Если ответ получен — кладём подмножество полей в `additional_info`,
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

    with SubscriberDirectoryClient() as client, db.SessionLocal() as session:
        while True:
            items = _fetch_pending_batch(session, batch_size, skip_ids)
            if not items:
                break

            for item in items:
                payload = client.fetch_subscriber(item.key)
                if payload is None:
                    failed += 1
                    skip_ids.add(item.id)
                    continue

                try:
                    item.additional_info = _extract_additional_info(payload)
                    item.status = "processed"
                    # Коммит после КАЖДОЙ успешной записи. Дороже, чем один
                    # commit на батч, зато при сбое посередине уже обработанные
                    # строки гарантированно сохранены — ничего не откатывается.
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
