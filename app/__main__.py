"""Точка входа batch-режима: один прогон обогащения и выход.

Запускается через `python -m app`. Используется в Docker-контейнере как CMD:
один цикл — обработали всех `pending` — выходим с кодом 0. В реальной системе
этим управляет cron / Kubernetes Job / очередь сообщений.
"""

from app.config import settings
from app.enricher import run_enrichment
from app.logging_setup import setup_logging


def main() -> None:
    setup_logging(settings.log_level)
    run_enrichment()


if __name__ == "__main__":
    main()
