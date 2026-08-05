FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

RUN uv run playwright install --with-deps chromium

COPY src/ ./src/
RUN uv sync --frozen

ENTRYPOINT ["uv", "run", "python", "-m", "notes_ai.main"]