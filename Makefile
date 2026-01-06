.PHONY: run test lint format alembic docker-up backup

run:
	uv run uvicorn studying_light.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run black .

alembic:
	uv run alembic upgrade head

docker-up:
	docker compose --env-file .env up --build

backup:
	uv run python -m studying_light.db.backup
