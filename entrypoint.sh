#!/bin/sh
set -e

echo "[entrypoint] applying migrations..."
alembic upgrade head

echo "[entrypoint] seeding test data (idempotent)..."
python -m app.seed --count 10

echo "[entrypoint] starting: $*"
exec "$@"
