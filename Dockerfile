FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock  README.md ./
RUN uv sync --frozen --no-install-project
COPY src/ ./src/
RUN uv run playwright install --with-deps chromium


RUN uv sync --frozen


ENTRYPOINT ["uv", "run", "uvicorn", "notes_ai.api.app:app", "--host", "0.0.0.0", "--port", "8000"]