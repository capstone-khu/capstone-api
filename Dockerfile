# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --group audio --group vision

COPY . .
RUN uv sync --frozen --no-dev --group audio --group vision

FROM python:3.12-slim AS runtime

RUN useradd -m -u 1000 appuser
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libegl1 libegl-mesa0 libglib2.0-0 libgles2 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=appuser:appuser /app /app

RUN mkdir -p /app/media/recordings /app/media/duet && chown -R appuser:appuser /app/media

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && fastapi run app/main.py --host 0.0.0.0 --port 8000 --workers 1"]
