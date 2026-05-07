# mts-data-enricher

Сервис на Python, который читает записи из PostgreSQL, обогащает их данными из публичного REST API ([JSONPlaceholder](https://jsonplaceholder.typicode.com/)) и сохраняет обратно.

Тестовое задание МТС — стажёр Python-разработчик.

## Стек

- Python 3.14, Poetry
- PostgreSQL, SQLAlchemy 2.x (`Mapped` / `mapped_column`), Alembic
- httpx, pydantic-settings
- pytest, pytest-mock, testcontainers
- ruff (lint + format)
- Docker (multi-stage), docker-compose
- FastAPI — минимальный UI (бонус)

## Запуск

_Будет описано по мере реализации шагов._

## Структура проекта

```
mts-data-enricher/
├── app/             # код сервиса
├── tests/           # тесты
├── migrations/      # alembic (появится позже)
├── .env.example
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```
