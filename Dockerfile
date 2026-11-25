FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /bin/

RUN useradd --create-home --shell /bin/bash app

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
COPY adk_dev ./adk_dev

RUN uv pip install --no-cache .

USER app

CMD ["uvicorn", "pawdesk.bootstrap.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
