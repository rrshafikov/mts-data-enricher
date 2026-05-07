# syntax=docker/dockerfile:1.7

# ---------- builder ----------
FROM python:3.14-slim AS builder

ENV POETRY_VERSION=1.8.5 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

# Сначала только манифесты — лучшее кеширование слоёв.
COPY pyproject.toml poetry.lock README.md ./

# Только runtime-зависимости (без dev).
RUN poetry install --only main --no-root

# Дальше уже исходники + установка самого пакета.
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

RUN poetry install --only main


# ---------- runtime ----------
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "app"]
