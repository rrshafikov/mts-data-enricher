import argparse
import logging
import random

from sqlalchemy import func, select

from app import db
from app.logging_setup import setup_logging
from app.models import Item

logger = logging.getLogger(__name__)

# Демо-API DummyJSON знает абонентов с id 1..208. Берём из этого диапазона.
_API_KEY_MIN = 1
_API_KEY_MAX = 208


def _existing_keys() -> set[str]:
    with db.SessionLocal() as session:
        return set(session.scalars(select(Item.key)))


def _insert_pending(keys: list[str]) -> int:
    with db.SessionLocal() as session:
        session.add_all([Item(key=k, status="pending") for k in keys])
        session.commit()
    return len(keys)


def _pick_unique_keys(count: int, exclude: set[str]) -> list[str]:
    """Выбирает `count` уникальных id из валидного диапазона.

    Возвращает максимум столько, сколько свободных id осталось — чтобы
    повторные «добавь pending» не уходили в бесконечный цикл, если кто-то
    задал count больше доступного диапазона.
    """
    pool = [str(i) for i in range(_API_KEY_MIN, _API_KEY_MAX + 1) if str(i) not in exclude]
    return random.sample(pool, k=min(count, len(pool)))


def seed_if_empty(count: int = 10) -> int:
    """Идемпотентно засеивает таблицу `count` записями с id 1..count.

    Если в таблице уже что-то есть — ничего не делает. Используется
    в entrypoint контейнера: повторный `docker compose up` не плодит дубли
    и не падает (требование ТЗ).
    """
    with db.SessionLocal() as session:
        existing = session.scalar(select(func.count()).select_from(Item)) or 0
    if existing:
        logger.info("Items table has %d rows, skipping seed", existing)
        return 0

    keys = [str(i) for i in range(1, count + 1)]
    added = _insert_pending(keys)
    logger.info("Seeded %d pending subscribers", added)
    return added


def add_pending(count: int = 5) -> int:
    """Добавляет `count` новых pending-записей со случайными id из API-диапазона.

    Используется UI-кнопкой «Добавить pending». Гарантирует, что новые id
    не пересекаются с уже существующими в таблице.
    """
    keys = _pick_unique_keys(count, exclude=_existing_keys())
    if not keys:
        logger.info("No free api keys left in range %d..%d", _API_KEY_MIN, _API_KEY_MAX)
        return 0
    added = _insert_pending(keys)
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
