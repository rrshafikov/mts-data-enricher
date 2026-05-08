import argparse
import logging
import random

from sqlalchemy import func, select

from app import db
from app.logging_setup import setup_logging
from app.models import Item

logger = logging.getLogger(__name__)


def _generate_phone() -> str:
    """Генерирует валидный российский мобильный номер: +79XXXXXXXXX."""
    operator = random.randint(900, 999)
    rest = random.randint(0, 9_999_999)
    return f"+7{operator}{rest:07d}"


def _generate_unique_phones(count: int, exclude: set[str]) -> list[str]:
    phones: set[str] = set()
    while len(phones) < count:
        candidate = _generate_phone()
        if candidate not in exclude and candidate not in phones:
            phones.add(candidate)
    return list(phones)


def _existing_keys() -> set[str]:
    with db.SessionLocal() as session:
        return set(session.scalars(select(Item.key)))


def _insert_pending(keys: list[str]) -> int:
    with db.SessionLocal() as session:
        session.add_all([Item(key=k, status="pending") for k in keys])
        session.commit()
    return len(keys)


def seed_if_empty(count: int = 10) -> int:
    """Идемпотентно засеивает таблицу `count` абонентами с уникальными телефонами.

    Если в таблице уже что-то есть — ничего не делает. Используется
    в entrypoint контейнера: повторный `docker compose up` не плодит дубли
    и не падает (требование ТЗ).
    """
    with db.SessionLocal() as session:
        existing = session.scalar(select(func.count()).select_from(Item)) or 0
    if existing:
        logger.info("Items table has %d rows, skipping seed", existing)
        return 0

    phones = _generate_unique_phones(count, exclude=set())
    added = _insert_pending(phones)
    logger.info("Seeded %d pending subscribers", added)
    return added


def add_pending(count: int = 5) -> int:
    """Добавляет `count` новых pending-записей со свежими уникальными телефонами.

    Используется UI-кнопкой «Добавить pending». Гарантирует, что новые номера
    не пересекаются с уже существующими в таблице.
    """
    phones = _generate_unique_phones(count, exclude=_existing_keys())
    added = _insert_pending(phones)
    logger.info("Added %d pending subscribers", added)
    return added


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Заполнить таблицу items тестовыми pending-записями"
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Сколько записей добавить (default: 10)"
    )
    args = parser.parse_args()
    setup_logging()
    seed_if_empty(args.count)


if __name__ == "__main__":
    main()
