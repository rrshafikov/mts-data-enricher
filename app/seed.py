import argparse
import logging

from sqlalchemy import func, select

from app.db import SessionLocal
from app.logging_setup import setup_logging
from app.models import Item

logger = logging.getLogger(__name__)


def seed(count: int = 10) -> int:
    """Добавляет `count` тестовых записей со статусом `pending`.

    Идемпотентно: если в таблице уже есть строки — ничего не делает.
    Это нужно, чтобы повторный `docker-compose up` не плодил дубли.

    Returns:
        Сколько строк реально добавлено (0, если seed пропущен).
    """
    with SessionLocal() as session:
        existing = session.scalar(select(func.count()).select_from(Item)) or 0
        if existing:
            logger.info("Items table has %d rows, skipping seed", existing)
            return 0

        items = [Item(key=str(i), status="pending") for i in range(1, count + 1)]
        session.add_all(items)
        session.commit()
        logger.info("Seeded %d pending items", len(items))
        return len(items)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Заполнить таблицу items тестовыми pending-записями"
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Сколько записей добавить (default: 10)"
    )
    args = parser.parse_args()
    setup_logging()
    seed(args.count)


if __name__ == "__main__":
    main()
