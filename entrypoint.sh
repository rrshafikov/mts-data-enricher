#!/bin/sh
# Единая точка входа для всех контейнеров приложения. Делает три шага:
#   1) накатывает миграции (idempotent — alembic пропустит уже применённые);
#   2) засеивает тестовые данные (idempotent — пропустит, если таблица не пуста);
#   3) запускает CMD контейнера.
# Тот же скрипт используется и `app`-контейнером (CMD: python -m app),
# и `web`-контейнером (CMD: uvicorn …). Шаги 1-2 безопасно повторяются.
set -e

echo "[entrypoint] applying migrations..."
alembic upgrade head

echo "[entrypoint] seeding test data (idempotent)..."
python -m app.seed --count 10

echo "[entrypoint] starting: $*"
exec "$@"
