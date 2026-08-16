# mts-data-enricher

Сервис на Python, который читает записи из PostgreSQL, обогащает их данными из публичного REST API и сохраняет обратно.

Тестовое задание МТС - стажёр Python-разработчик.

## Что делает

1. Берёт из таблицы `items` строки со `status='pending'`.
2. Для каждой строки делает запрос к внешнему API по значению из `key`.
3. Складывает подмножество полей ответа (ФИО, телефон, email, возраст, город) в `additional_info` как JSON и ставит `status='processed'`.
4. Если API недоступен или вернул ошибку, сервис логгирует и идёт дальше, не валит обработку остальных записей.
5. На повторный запуск без `pending`-записей просто завершается с `processed=0 failed=0`.

В качестве внешнего API используется [DummyJSON](https://dummyjson.com/) (`/users/{id}`) - публичный аналог JSONPlaceholder.

## Стек

| Слой | Реализация |
|---|---|
| Язык | Python 3.14 |
| Менеджер зависимостей | Poetry |
| ORM / БД | SQLAlchemy 2.x (`Mapped`/`mapped_column`) + Alembic + PostgreSQL 16 |
| HTTP-клиент | httpx |
| Конфиг | `python-dotenv` + класс `Settings` поверх `os.getenv` |
| Логирование | `logging` (stdlib), вывод в stdout |
| Тесты | pytest + pytest-mock + respx (HTTP) + testcontainers-postgres (реальная PG в контейнере) |
| Линт/формат | ruff |
| Контейнеризация | multi-stage Dockerfile + docker-compose |
| CI | GitHub Actions (lint + tests + docker build) |
| UI (бонус сверх ТЗ) | FastAPI + Jinja2 |

## Быстрый старт

Требуется только Docker.

```bash
docker compose up --build
```

Что произойдёт:
1. Поднимется PostgreSQL.
2. `app`-контейнер накатит миграции, засеет 10 тестовых строк (`status='pending'`), пройдётся по ним и обогатит. Завершится с кодом 0.
3. `web`-контейнер поднимет UI на http://localhost:8000.

Повторный `docker compose up` ничего не сломает: миграции и seed идемпотентны, обогащать тоже нечего → `processed=0 failed=0`.

Полная очистка (включая БД-volume):

```bash
docker compose down -v
```

## Локальная разработка

Нужен Python 3.14 и Poetry.

```bash
poetry env use 3.14
poetry install

cp .env.example .env

# Тесты
poetry run pytest

# Линтеры
poetry run ruff check .
poetry run ruff format --check .

# Запустить сидинг и обогащение против локальной БД (предполагает запущенный db-контейнер)
poetry run alembic upgrade head
poetry run python -m app.seed --count 10
poetry run python -m app
```

## Конфигурация

Все параметры читаются из `.env` (а внутри Docker - из `environment` в `docker-compose.yml`). См. [.env.example](.env.example).

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | хост PG |
| `POSTGRES_PORT` | `5432` | порт PG |
| `POSTGRES_USER` | `enricher` | пользователь PG |
| `POSTGRES_PASSWORD` | `enricher` | пароль PG |
| `POSTGRES_DB` | `enricher` | имя базы |
| `API_BASE_URL` | `https://dummyjson.com` | базовый URL внешнего API |
| `API_PATH` | `/users/{key}` | шаблон пути; плейсхолдер `{key}` подставляется из `items.key` |
| `API_TIMEOUT` | `10.0` | тайм-аут на один запрос (сек) |
| `BATCH_SIZE` | `50` | размер батча выборки `pending` |
| `LOG_LEVEL` | `INFO` | уровень логирования |

## Как переключиться на свой API/данные

**Через `.env` (без правки кода):**
- Поменять `API_BASE_URL` и `API_PATH` на свой эндпоинт. Если ваш API ожидает не `id`, а, скажем, артикул, — задайте `API_PATH=/api/v1/items/{key}`.
- Подключиться к своей БД - поменять `POSTGRES_*`.
- Не использовать наш seed - заранее наполнить таблицу `items` своим SQL'ем; наш seed увидит существующие строки и пропустится (см. [app/seed.py](app/seed.py)).

**Что специфично для конкретной интеграции (одна строка кода):**
- Какие поля выбираем из ответа API → [app/enricher.py](app/enricher.py): функция `_extract_additional_info`. Сейчас собирает `firstName, lastName, phone, email, age, city`.

## Архитектура

```
┌─────────┐  pending  ┌──────────┐  GET   ┌────────────┐
│   db    │◄─────────►│   app    │◄──────►│ external   │
│  (PG)   │ processed │ (worker) │  JSON  │ API (HTTP) │
└─────────┘           └──────────┘        └────────────┘
     ▲
     │ read-only / triggers
     │
┌──────────┐
│   web    │  http://localhost:8000  (бонус сверх ТЗ)
│ (FastAPI)│
└──────────┘
```

Несколько решений, которые стоит проговорить:

- **Per-item commit** в [app/enricher.py](app/enricher.py): коммит после каждой успешной записи. Дороже, чем один commit на батч, зато при сбое посередине уже обработанные строки сохранены.
- **`skip_ids`** там же: записи, которые в текущем запуске не получилось обработать, исключаются из последующих SELECT'ов того же запуска, иначе цикл вечно повторял бы провальные.
- **Healthcheck в compose**: `app` ждёт `db: service_healthy`, `web` ждёт `app: service_completed_successfully`. Это сериализует миграции и seed между сервисами.
- **Multi-stage Dockerfile**: Poetry и dev-зависимости остаются в build-стадии, в runtime-образ попадает только `.venv` с прод-зависимостями.

## Структура

```
mts-data-enricher/
├── app/
│   ├── __main__.py          # точка входа batch-режима (CMD контейнера)
│   ├── config.py            # Settings из .env через python-dotenv
│   ├── db.py                # engine + session factory
│   ├── models.py            # Item: id, key, additional_info, status
│   ├── api_client.py        # SubscriberDirectoryClient (httpx)
│   ├── enricher.py          # основной цикл обогащения
│   ├── seed.py              # seed_if_empty / add_pending
│   ├── logging_setup.py
│   └── web/                 # FastAPI UI (бонус)
│       ├── main.py
│       ├── templates/
│       └── static/
├── migrations/              # Alembic
├── tests/                   # pytest + testcontainers + respx
├── .github/workflows/ci.yml # lint + tests + docker build
├── Dockerfile               # multi-stage
├── docker-compose.yml       # db + app + web
├── entrypoint.sh            # миграции → seed → CMD
├── pyproject.toml
└── .env.example
```

## CI

[.github/workflows/ci.yml](.github/workflows/ci.yml) запускается на push в `main` и на PR в `main`:

- **lint** - `ruff check` + `ruff format --check`
- **test** - `pytest` (поднимает PG через testcontainers; ubuntu-runners уже имеют Docker)
- **docker** - сборка образа из Dockerfile с GHA-кешем слоёв
