.PHONY: sync up down migrate seed lint test test-int eval adk-web chat

sync:
	uv sync --extra dev

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	docker compose run --rm api alembic upgrade head

seed:
	docker compose run --rm api python -m pawdesk.bootstrap.seed

lint:
	uv run ruff check .
	uv run mypy src
	uv run lint-imports

test:
	uv run pytest tests/unit tests/agents tests/e2e -v

test-int:
	uv run pytest tests/contract tests/integration -v

eval:
	uv run adk eval adk_dev/pawdesk_dev evals/evalsets/mvp_read_flow.evalset.json

adk-web:
	docker compose --profile dev up adk-web

chat:
	uv run python scripts/simulate_chat.py
