# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

RUN useradd -m -u 1000 appuser
WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && fastapi run app/main.py --host 0.0.0.0 --port 8000"]
